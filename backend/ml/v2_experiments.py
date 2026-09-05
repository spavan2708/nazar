"""Train-only grouped model selection. No final evaluation access in this module."""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, average_precision_score, brier_score_loss, log_loss)

SEED = 42
THRESHOLD = .65
CANDIDATES = [
    {'kind':'lr', 'C':c, 'class_weight':weight}
    for c in (.1, 1., 10., 100.) for weight in (None, 'balanced')
] + [
    {'kind':'lr_sigmoid', 'C':c, 'class_weight':'balanced'} for c in (1., 10.)
] + [
    {'kind':'svm_sigmoid', 'C':c, 'class_weight':'balanced'} for c in (.1, 1., 10.)
]


def folds(y, groups, n=5):
    return list(StratifiedGroupKFold(n_splits=n, shuffle=True, random_state=SEED).split(np.zeros(len(y)), y, groups))


def estimator(spec, y, groups):
    args = dict(C=spec['C'], class_weight=spec['class_weight'], random_state=SEED, max_iter=10000)
    base = LinearSVC(**args) if spec['kind'] == 'svm_sigmoid' else LogisticRegression(**args)
    if spec['kind'].endswith('sigmoid'):
        # Explicit inner group folds prevent translated variants leaking into calibration.
        return CalibratedClassifierCV(base, method='sigmoid', cv=folds(y, groups, 3), ensemble=True)
    return base


def probability(model, X):
    return model.predict_proba(X)[:, list(model.classes_).index(1)]


def metrics(y, p, threshold=THRESHOLD):
    y, p = np.asarray(y), np.asarray(p)
    pred = p >= threshold
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0,1]).ravel()
    both = len(set(y)) == 2
    return dict(n=len(y), accuracy=float(accuracy_score(y,pred)),
        precision=float(precision_score(y,pred,zero_division=0)), recall=float(recall_score(y,pred,zero_division=0)),
        f1=float(f1_score(y,pred,zero_division=0)), confusion_matrix=[[int(tn),int(fp)],[int(fn),int(tp)]],
        roc_auc=float(roc_auc_score(y,p)) if both else None,
        pr_auc=float(average_precision_score(y,p)) if both else None,
        brier=float(brier_score_loss(y,p)), log_loss=float(log_loss(y,p,labels=[0,1])),
        fp=int(fp), fn=int(fn), threshold=threshold)


def reliability(y, p):
    y, p = np.asarray(y), np.asarray(p)
    rows = []
    for low, high in zip(np.arange(0,1,.2), np.arange(.2,1.01,.2)):
        mask = (p >= low) & ((p < high) if high < .99 else (p <= high))
        if mask.any():
            rows.append(dict(lower=float(low), upper=float(high), n=int(mask.sum()),
                mean_probability=float(p[mask].mean()), observed_fraction=float(y[mask].mean())))
    ece = sum(r['n'] * abs(r['mean_probability'] - r['observed_fraction']) for r in rows) / len(y)
    return dict(bins=rows, ece=ece)


def select(X, y, groups, candidates=None):
    y, groups = np.asarray(y), np.asarray(groups)
    results = []
    outer = folds(y, groups)
    for spec in candidates or CANDIDATES:
        oof = np.zeros(len(y))
        for train, valid in outer:
            model = estimator(spec, y[train], groups[train])
            model.fit(X[train], y[train])
            oof[valid] = probability(model, X[valid])
        results.append(dict(spec=spec, metrics=metrics(y,oof), calibration=reliability(y,oof)))
    # Preregistered selection policy: F1 at unchanged .65; Brier, then AP tie-breaks.
    # No threshold or candidate can be chosen using final held-out outcomes.
    winner = max(results, key=lambda r:(r['metrics']['f1'], -r['metrics']['brier'], r['metrics']['pr_auc']))
    model = estimator(winner['spec'], y, groups)
    model.fit(X,y)
    return model, winner, results

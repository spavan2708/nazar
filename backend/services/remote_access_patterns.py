"""Small compositional request patterns; canonical scoring remains in text_analyzer."""
import re

REMOTE_SAFETY = (
    'never install', "don't install", 'never download', 'do not download',
    'do not allow', "don't allow", 'never allow', 'do not let', "don't let",
    'install mat karo', 'install panna vendam',
)


def remote_access_request(text: str) -> bool:
    # Keep concepts within a bounded clause; unrelated sentences must not combine.
    for clause in re.split(r'[.!?;।\n]', text):
        if len(clause) > 600:
            # Bounded windows retain local context without a whole-message word bag.
            windows = (clause[start:start + 300] for start in range(0, len(clause), 150))
        else:
            windows = (clause,)
        for part in windows:
            action = re.search(r'\b(?:install|download|open|run|launch|start)\b', part)
            remote_tool = re.search(r'\b(?:anydesk|teamviewer|remote(?:[- ]+(?:support|access|desktop|control))?[- ]+(?:app(?:lication)?|software|tool|program))\b', part)
            support_tool = re.search(r'\bsupport[- ]+(?:app(?:lication)?|software|tool|program)\b', part)
            connection = re.search(r'\b(?:connect|control|access|share)\b', part)
            allow = re.search(r'\b(?:allow|let|give|grant)\b', part)
            operator = re.search(r'\b(?:agent|technician|executive)\b', part)
            device_target = re.search(r'\b(?:to|of)\s+(?:your|my|the)\s+(?:device|computer|phone|screen)\b', part)
            remote_control = re.search(r'\b(?:remote[- ]+(?:access|control|connection)|screen[- ]sharing|control\b.{0,60}\b(?:device|computer|phone)\b.{0,30}\bremotely|remotely\b.{0,30}\bcontrol)\b', part)
            if (action and (remote_tool or (support_tool and connection) or remote_control)
                    or allow and (remote_control or operator and connection and device_target)):
                return True
    return False

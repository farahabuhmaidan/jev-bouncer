"""Every question Jev is asked, in one place (design/03-jev-questions.md).

Jev answers judgments; it never picks the action. server/policy.py turns these
answers into interrupt / batch / delegate / drop. Question ids are for code
only: they are not sent to the model, so each instruction is a full question.
State paths in backticks refer to fields built by pipeline/state.py.
"""


def noul(instructions: str, true: str, false: str) -> dict:
    return {"type": "noul", "instructions": instructions, "criteria": {"true": true, "false": false}}


MESSAGE_QUESTIONS = {
    "needs_sanad": noul(
        "Does Sanad need to handle `message` himself?",
        "Only Sanad has the knowledge, ownership or authority to act on it, for example it is about a ticket or "
        "decision he owns, or the sender asks for him specifically about his own work.",
        "A teammate, the support or DevOps team, a doc or anyone on the team could answer or handle it just as well.",
    ),
    "time_sensitive": noul(
        "Will waiting until Sanad's next free slot cause real harm?",
        "Something breaks or stays broken for customers, a release or the investor demo is put at risk, money is "
        "lost, a person or child needs care, or a deadline today is missed if this waits a few hours.",
        "It would be just as useful answered in a few hours or tomorrow; nothing gets worse in the meantime.",
    ),
    "wording_only_urgency": noul(
        "Does `message` sound urgent while nothing in it is actually time-critical?",
        "It uses urgent wording such as caps, URGENT, ASAP or several exclamation marks about something that can "
        "safely wait, such as a cosmetic change to a slide or a preference.",
        "It does not sound urgent, or it sounds urgent and the urgency is real (something is broken or a person needs help).",
    ),
    "family_matter": noul(
        "Is `message` about Sanad's family or personal life?",
        "It comes from or is about his partner, his child, the child's school, his home or his health.",
        "It is about work: product, code, customers, colleagues or company matters.",
    ),
    "blocks_release": noul(
        "Does `message` report something broken or missing that would stop today's release, tomorrow's investor "
        "demo or a ticket due today from working?",
        "A bug, outage, failing flow or missing piece that stops one of these from working, for example wrong prices "
        "in checkout or errors in production.",
        "It is unrelated to them, or it is a cosmetic or optional change such as a slide's colour or wording.",
    ),
    "is_noise": noul(
        "Is `message` informational with nothing for Sanad to do or reply to?",
        "Newsletters, marketing, automated status notifications, reminders he already has, or a plain thanks or reaction.",
        "It asks a question, requests something, or carries information Sanad needs to act on or reply to.",
    ),
    "urgency": {
        "type": "score",
        "instructions": "How soon does `message` need a response from Sanad?",
        "criteria": [
            "It can wait days, or needs no response at all.",
            "It should be answered sometime this week.",
            "It should be answered today, but a few hours of delay is fine.",
            "It should be answered within the hour.",
            "It needs action within minutes: something is broken, a person needs help, or a deadline is about to pass.",
        ],
    },
}

CI_QUESTIONS = {
    "failure_type": {
        "type": "choice",
        "instructions": "What caused the CI failure shown in `ci.log_tail`?",
        "criteria": {
            "flaky_test": "An intermittent test failure such as a timeout or ordering issue, unrelated to the change in "
                          "`ci.commit_message`; the same test passes on rerun.",
            "code_regression": "The change in `ci.commit_message` broke behaviour that the failing test checks; the "
                               "assertion shows a wrong value.",
            "infra_problem": "The CI machinery failed: runner, network, registry, disk or permissions errors; no test "
                             "actually ran or the failure is outside the code.",
            "config_or_lint": "Lint, formatting, type-check or configuration errors in the changed files.",
        },
    },
    "cause_identifiable": noul(
        "Does `ci.log_tail` show what made the run fail?",
        "The log names a failing test, error or step clearly enough to tell what went wrong.",
        "The log is cut off, empty or too vague to tell what failed.",
    ),
    "blocks_release": noul(
        "Is this CI failure on the investor demo branch or a release branch, given `ci.branch` and `linked_items`?",
        "The failing branch is the investor-demo branch, main for a release planned today, or a branch for a ticket due today.",
        "The failing branch is a feature branch for work that is not due today.",
    ),
}


# Asked in a second request, only when code found a future date in the message (design/16).
REMINDER_QUESTIONS = {
    "task_later": noul(
        "Does `message` ask Sanad to do something himself at a later date?",
        "It gives Sanad a task with a future date: pay, book, renew, send, attend or prepare something then.",
        "It only shares news or plans, mentions a date for something Sanad does not have to act on, or the task is for someone else.",
    ),
}


def questions_for(event_type: str) -> dict:
    if event_type == "reminder":
        return REMINDER_QUESTIONS
    return CI_QUESTIONS if event_type == "ci_failure" else MESSAGE_QUESTIONS

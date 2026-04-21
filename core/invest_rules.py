# -*- coding: utf-8 -*-
"""
invest_rules.py — 1–5 scale version (for assertion_rules.py Route B)

Purpose
-------
- Provide INVEST_RUBRIC_15 textual definitions for 1–5 scale.
- Provide helper function `get_invest_rubric_text()` for retrieval.
- Centralize rubric content to keep logic decoupled from assertions.
Author: YOU
"""

# --- Dimensions ---------------------------------------------------------------
DIM_KEYS = ["I", "N", "V", "E", "S", "T"]

# --- INVEST Rubric (1–5 Scale) ------------------------------------------------
INVEST_RUBRIC_15 = {
  "I": {
    "1": "The story is explicitly blocked by or dependent on the completion of other specific stories. It cannot be started until others are finished.",
    "2": "The story can be started, but its core business rules or decision logic are defined in, or shared with, another specific story. A developer reading this story alone cannot determine the full decision logic without consulting another story. (e.g., “As a user, I want to apply for a discount using the same eligibility rules as the membership upgrade flow, so that my pricing is consistent.”) ",
    "3": "The story describes a standalone feature, but it operates on objects, records, or account states that must exist before the story is meaningful in production. The build work is separable, but the story still depends on prior conditions for full validation. The dependency is on existence of data, not on shared logic.(e.g., “As a returning customer, I want to view my past order history, so that I can reorder items quickly.”)",
    "4": "The story can be developed and implemented independently, with dependencies limited to shared interfaces or system components. These dependencies do not significantly constrain development or validation. (e.g., “Allow users to reset their password via the existing email service.”)",
    "5": "The story is fully self-contained; it can be developed and released independently, with no blocking dependencies or required sequencing. No external conditions are required for development or validation.  (e.g., “Allow users to change their account password.”)"
  },
  
  "N": {
    "1": "The story dictates specific technical implementations (e.g., SQL queries, database fields, specific algorithms), leaving no room for alternative solutions.",
    "2": "The story names a specific UI component or interaction element (e.g., a button, dropdown, modal, sidebar, form field, or navigation pattern). The user's goal may be stated, but the interface solution is decided before the team has discussed it. Backend and logic decisions remain open. However, the solution is highly constrained at the presentation level. (e.g., \"As a user, I want a dropdown menu in the top navigation bar to select my preferred language, so that the site displays in my language.\")",
    "3": "The story describes a specific system behavior, response channel, or process sequence rather than the user's outcome. No UI component is named, but the story commits to how the system will act, specifying a notification method, a workflow step, or a processing sequence where alternatives exist. The team can choose the interface but cannot reconsider the behavioral approach. (e.g., \"As a user, I want to receive an email confirmation after completing checkout, so that I know my order was placed.\")",
    "4": "The story clearly states the user's goal and rationale. Technical implementation is open, while only necessary constraints (e.g., policy, compliance or rules) are defined. These constraints do not significantly limit the range of possible solutions.",
    "5": "The story defines a pure business problem or user need, with no solution implied. It invites the team to co-create the best solution (UI/Tech) during refinement, with no predefined constraints on implementation."
  },
  
  "V": {
    "1": "Describes a developer task (e.g., 'refactor code', 'create table') with no discernible user or business value.",
    "2": "The benefit clause describes the direct result of completing the action, what is true immediately after the user does the thing, rather than explaining why that result matters. The 'so that' restates the action as a completed state, an access condition, or a system confirmation. It tells you the feature worked, it does not tell you what the user can now do, avoid, or accomplish because of it. (e.g., 'As a user, I want to submit my timesheet so that my timesheet is submitted.', 'As a member, I want to log in so that I am logged in and can access the site.', 'As a customer, I want to place an order so that the order is placed in the system.')",
    "3": "The benefit clause names a positive direction (e.g., saving time, improving experience, increasing efficiency) but does not specify who benefits, in what situation, or compared to what baseline. The value is plausible but generic: the same 'so that' clause could be transplanted onto several other stories in the backlog without sounding wrong. A product team cannot use this benefit to prioritize, validate, or measure the story. (e.g., Vague outcome: \"As a returning customer, I want to view my previous orders, so that I can save time when reordering.\" Experience claim: \"As a new user, I want guided setup steps during onboarding, so that the experience is easier and less confusing.\")",
    "4": "The story names a specific persona and states a concrete, user-facing benefit (something the user can now do, avoid, or achieve that they could not before). The value is specific enough that it could not be transplanted to another story without sounding wrong. The user outcome is clear and actionable, even without explicit business metrics.(e.g., Positive gain: 'As a field technician, I want to access equipment manuals offline, so that I can complete repairs without waiting for network connectivity.' Loss prevention: 'As a writer, I want my draft saved automatically every two minutes, so that I don't lose work if my browser crashes.')",
    "5": "The story articulates clear value for a specific persona while also linking the feature to measurable business outcomes or key results. The value is both user-relevant and quantitatively assessable.(e.g., “Reduce manual support requests for ticket sales by 10%.”)"
  },
  
  "E": {
    "1": "The story names no concrete system behavior. It may express a desired quality, an organizational goal, or a general improvement, but it does not describe what the system should do or enable. No shared mental model of the work can be formed from the text alone. Estimation cannot begin. (e.g., As a user, I want the system to be better and more reliable, so that I can trust it.)",
    "2": "The story names a recognizable system action but provides no scope boundaries — no limits, conditions, formats, quantities, or exclusions. The team knows roughly what to build, but cannot agree on where it starts and stops. Estimates will vary widely across developers because each person will assume different scope boundaries. (e.g., As a user, I want to search for products, so that I can find what I need.)",
    "3": "The story names a system action and defines its primary scope. However, acceptance conditions are absent or incomplete: success criteria are not stated, failure paths are not specified, or edge cases are left to inference. The team can estimate the core work but risks underestimating because hidden complexity in the uncovered conditions will emerge during development. (e.g., As a user, I want to export my reports, so that I can analyze data outside the system.)",
    "4": "The story defines a concrete action with explicitly stated boundaries. The scope does not rely on inference or domain knowledge and can be interpreted consistently across developers. (e.g., 'As a user, I want to mark an item as a favorite, which saves it to my Favorites list, so that I can find it quickly later.')",
    "5": "The story specifies a concrete action, clear scope boundaries, and all acceptance conditions, including success paths, failure paths, and edge cases. No domain knowledge or inference is required to estimate. Two developers reading this story independently will produce the same estimate.(e.g., As a site admin, I want jobs posted more than 30 days ago to be automatically unpublished, so that listings that may have been filled are not shown to visitors.)"
  },
  
  "S": {
    "1": "The story covers a broad feature/module and end-to-end workflow. The scope is too large to be treated as a single user story and clearly requires major breakdown. (e.g., As a user, I want a complete account management system, so that I can control all aspects of my profile, security, and preferences.)",
    "2": "The story combines multiple independent user goals in a single statement, typically joined by AND, OR, or an implicit sequence of distinct actions. Each goal could stand alone as a separate story. The story must be split before development begins.(e.g., \"As a user, I want to search for products, view product details, and save items to a wish list, so that I can plan my purchases.\")",
    "3": "The story expresses a single user goal but includes multiple conditions that require separate development and testing effort, meaning they cannot be delivered as one atomic unit. A developer completing this story must make multiple independent implementation decisions. The story could be split into smaller deliverables without losing coherence. (e.g., As a registered user, I want to receive a confirmation email after placing an order and be able to view the order summary in my account dashboard, so that I have a record of my purchase.”)",
    "4": "The story expresses a single user goal through a single primary path. Any variation present (e.g., alternative inputs, minor edge cases) is handled within a single development effort and does not require separate deliverables. The story is sprint-ready, but a developer will need to make internal sequencing decisions during implementation. (e.g., As a user, I want to search for products by name or category, so that I can find what I am looking for quickly.”)",
    "5": "The story captures one user action with a clearly bounded outcome and no variation requiring conditional logic. A developer can implement it as a single unit with no internal branching decisions driven by the story itself. (e.g., “As a site admin, I want jobs posted more than 30 days ago to be automatically unpublished, so that filled positions are not shown to visitors.”)"
  },
  
  "T": {
    "1": "Acceptance depends entirely on subjective judgment. The story uses evaluative language ('intuitive', 'nice', 'appealing', 'easy to use') that reflects an opinion rather than a system state. No two testers would observe the same thing or apply the same standard. (e.g., As a user, I want an attractive and intuitive interface, so that I enjoy using the application.)",
    "2": "The story names a feature or capability the user wants but does not describe any specific system behaviors a tester could observe. Expected behaviors is implied by the feature name — a tester knows roughly what area to investigate, but has no defined output, state change, or system response to target. (e.g., As a user, I want a personalized dashboard, so that I can access what I need quickly.)",
    "3": "The story describes a specific system behavior that a tester can locate and observe. However, the pass condition is defined relative to an unstated standard: a comparison point, a threshold, or a baseline that exists outside the story text. The tester can run the test but cannot reach a verdict without resolving a comparison that the story never makes explicit. Two testers observing an identical system output may disagree on whether it passes.(e.g., \"As a user, I want my dashboard to update automatically when new activity occurs, so that I always see the latest information without refreshing the page.\")",
    "4": "The expected outcome relies on a general description rather than a precise rule. A tester understands what to verify but must make minor interpretive decisions about boundary conditions. (e.g., As a user, I want to receive a notification when someone responds to my post, so that I can follow up while the conversation is still active.)",
    "5": "The story states acceptance conditions using specific numbers, dates, system states, or defined thresholds. Pass/fail is deterministic, any tester reading the story will reach the same verdict on the same input without discussion or interpretation.(e.g., “As a user, I want notifications older than 7 days to be automatically removed from my dashboard, so that I only see activity that is still relevant to me.”)"
  }
}



# === Thresholds (LM Assertion use) ===
def get_invest_rubric_text(dim: str, score: int, scale: str = "1-5") -> str:
    """供 Assertion 邏輯調用，獲取特定分數的文字描述"""
    if scale != "1-5":
        return ""
    dim = (dim or "").upper().strip()
    if dim not in INVEST_RUBRIC_15:
        return ""
    
    # 確保分數在 1-5 之間
    step = str(max(1, min(5, int(round(score)))))
    return INVEST_RUBRIC_15[dim]["scale"].get(step, "")

# thresholds & weights on 1–5
INVEST_THRESHOLDS = {d: 3.0 for d in DIM_KEYS}
INVEST_WEIGHTS = {d: 1.0 / len(DIM_KEYS) for d in DIM_KEYS}

INVEST_RUBRIC = INVEST_RUBRIC_15
"""
INVEST Rubric Definition
--------------------------------------
Defines detailed INVEST evaluation grid 0~3 scale
based on Annex A: INVEST Grid (Independent, Negotiable, Valuable, Estimable, Small, Testable)

Used by: dspy_signatures, assertion_rules, pipeline
"""

INVEST_RUBRIC = {
    "I": {
        "name": "Independent",
        "description": "User Stories should be as independent as possible.",
        "scale": {
            0: "The start of construction of a User Story is tied to the completion of at least one other User Story.",
            1: "The completion of a User Story hinders the start of construction of at least one other User Story.",
            2: "The User Story can contain any constraint, but its release can be constrained by the completion of at least one other User Story.",
            3: "The User Story is fully independent, and it can be realized and released without any constraint."
        }
    },
    "N": {
        "name": "Negotiable",
        "description": "User Stories should be 'open', reporting any relevant details as much as possible.",
        "scale": {
            0: "The User Story contains enough detail to be a technical specification (Design phase), leaving no room to negotiate any element.",
            1: "The User Story is written with enough detail to be a functional specification (Analysis phase), leaving no room to negotiate any element.",
            2: "The User Story is written with informative content defining a User Requirement in a consolidated manner, yet shared between Customer and Provider.",
            3: "The User Story is written with the informative content typical of a high-level need, allowing feedback between customer and provider."
        }
    },
    "V": {
        "name": "Valuable",
        "description": "User Stories should provide value to end users in terms of the solution.",
        "scale": {
            0: "The functional part of the User Story does not contain all the functionalities requested by the customer.",
            1: "The functional part expresses mostly qualitative and technical requirements about the system, and needs to be more developed in terms of functional requirements.",
            2: "The functional part expresses mostly the functional requirements requested by the customer, but also includes qualitative and technical requirements.",
            3: "The functional part of the User Story correctly expresses only the functional requirements requested by the customer."
        }
    },
    "E": {
        "name": "Estimable",
        "description": "Each User Story must be able to be estimated in terms of relative size and effort.",
        "scale": {
            0: "The User Story shows only its functional part, filled in by the customer, but without sufficient detail to allow the provider to fill in the qualitative/technical parts.",
            1: "The User Story shows only its functional part, filled in by the customer, but validated with the provider.",
            2: "The User Story has been completed by the provider with respect to qualitative/technical issues, but still needs to be validated jointly with the customer.",
            3: "All useful parts of the User Story (functional/qualitative/technical) are shown, allowing the effort needed to size and estimate it, and validated by both parts."
        }
    },
    "S": {
        "name": "Small",
        "description": "Each User Story should be sufficiently granular, and not defined at too high a level.",
        "scale": {
            0: "The User Story is very large and cannot be completed within a Sprint.",
            1: "The User Story is very large, and can be completed within a Sprint, but cannot accommodate the creation/delivery of other User Stories.",
            2: "The size of the User Story is such that it can be completed within a Sprint, jointly with other User Stories, but it is too small to create overhead about the Testing phase.",
            3: "The size of the User Story is such that it can be completed within a Sprint, jointly with other User Stories, ensuring an appropriate balance between development and testing activities."
        }
    },
    "T": {
        "name": "Testable",
        "description": "Each User Story must be formulated to stress useful details for creating tests.",
        "scale": {
            0: "The User Story does not include tips about Acceptance Tests.",
            1: "The User Story includes a formal indication of Acceptance Tests, but yet to be completed.",
            2: "The User Story includes an indication of Acceptance Tests which are complete, but yet to be validated.",
            3: "The User Story includes an indication of completed and validated Acceptance Tests."
        }
    }
}

# === Thresholds (LM Assertion use) ===
# Using original grid (0~3), rescaled to 0~5 model in later modules if needed
INVEST_THRESHOLDS = {
    "overall": 2.5,
    "I": 2,
    "N": 2,
    "V": 2,
    "E": 2,
    "S": 2,
    "T": 2.5
}

# === Optional weights (for overall computation) ===
# Increase influence of Testable and Valuable
INVEST_WEIGHTS = {
    "I": 1,
    "N": 1,
    "V": 2,
    "E": 1,
    "S": 1,
    "T": 2
}

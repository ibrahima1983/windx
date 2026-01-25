"""Factory data for generating sample manufacturing hierarchies.

This module contains pre-defined data pools used by the factory to generate
realistic but randomized product configuration hierarchies.
"""

# Manufacturing Type Templates
MANUFACTURING_TYPES = [
    {
        "name": "Casement Window",
        "description": "Energy-efficient casement windows with superior ventilation",
        "base_category": "window",
        "base_price": (200.00, 350.00),
        "base_weight": (15.00, 25.00),
    },
    {
        "name": "Double-Hung Window",
        "description": "Classic double-hung windows with easy cleaning",
        "base_category": "window",
        "base_price": (180.00, 320.00),
        "base_weight": (14.00, 22.00),
    },
    {
        "name": "Sliding Glass Door",
        "description": "Modern sliding glass doors with energy-efficient glazing",
        "base_category": "door",
        "base_price": (450.00, 800.00),
        "base_weight": (35.00, 60.00),
    },
    {
        "name": "Entry Door",
        "description": "Secure and stylish entry doors for residential use",
        "base_category": "door",
        "base_price": (300.00, 600.00),
        "base_weight": (25.00, 45.00),
    },
    {
        "name": "Patio Door",
        "description": "French-style patio doors with elegant design",
        "base_category": "door",
        "base_price": (500.00, 900.00),
        "base_weight": (40.00, 70.00),
    },
    {
        "name": "Bay Window",
        "description": "Architectural bay windows for enhanced views",
        "base_category": "window",
        "base_price": (800.00, 1500.00),
        "base_weight": (50.00, 90.00),
    },
    {
        "name": "Skylight",
        "description": "Roof-mounted skylights for natural lighting",
        "base_category": "window",
        "base_price": (400.00, 900.00),
        "base_weight": (20.00, 40.00),
    },
    {
        "name": "Garage Door",
        "description": "Insulated garage doors with automatic openers",
        "base_category": "door",
        "base_price": (600.00, 1200.00),
        "base_weight": (80.00, 150.00),
    },
]

# Category Templates (Level 0 - Root nodes)
CATEGORIES = [
    {
        "name": "Frame Options",
        "description": "Customize your frame material and finish",
        "ui_component": "section",
    },
    {
        "name": "Glass Options",
        "description": "Choose your glass configuration and coatings",
        "ui_component": "section",
    },
    {
        "name": "Hardware Options",
        "description": "Select locks, handles, and hinges",
        "ui_component": "section",
    },
    {
        "name": "Dimensions",
        "description": "Specify product dimensions",
        "ui_component": "section",
    },
    {
        "name": "Energy Features",
        "description": "Energy efficiency and insulation options",
        "ui_component": "section",
    },
    {
        "name": "Security Features",
        "description": "Enhanced security and safety options",
        "ui_component": "section",
    },
    {
        "name": "Aesthetic Options",
        "description": "Colors, finishes, and decorative elements",
        "ui_component": "section",
    },
    {
        "name": "Installation Options",
        "description": "Installation method and accessories",
        "ui_component": "section",
    },
]

# Attribute Templates (Level 1+ - Configurable properties)
ATTRIBUTES = {
    "Frame Options": [
        {
            "name": "Frame Material",
            "data_type": "selection",
            "required": True,
            "ui_component": "radio",
            "description": "Select the frame material",
            "help_text": "Different materials offer different benefits",
        },
        {
            "name": "Frame Color",
            "data_type": "selection",
            "required": True,
            "ui_component": "dropdown",
            "description": "Choose frame color",
            "help_text": "Custom colors may extend lead time",
        },
        {
            "name": "Frame Finish",
            "data_type": "selection",
            "required": False,
            "ui_component": "radio",
            "description": "Select surface finish",
            "help_text": "Finish affects durability and appearance",
        },
        {
            "name": "Frame Thickness",
            "data_type": "number",
            "required": False,
            "ui_component": "slider",
            "description": "Frame thickness in inches",
            "help_text": "Thicker frames provide better insulation",
        },
    ],
    "Glass Options": [
        {
            "name": "Pane Configuration",
            "data_type": "selection",
            "required": True,
            "ui_component": "radio",
            "description": "Number of glass panes",
            "help_text": "More panes provide better insulation",
        },
        {
            "name": "Glass Type",
            "data_type": "selection",
            "required": True,
            "ui_component": "dropdown",
            "description": "Type of glass",
            "help_text": "Different glass types for different needs",
        },
        {
            "name": "Glass Coating",
            "data_type": "selection",
            "required": False,
            "ui_component": "checkbox",
            "description": "Optional glass coatings",
            "help_text": "Coatings improve energy efficiency",
        },
        {
            "name": "Tint Level",
            "data_type": "selection",
            "required": False,
            "ui_component": "dropdown",
            "description": "Glass tint darkness",
            "help_text": "Tinting reduces glare and heat",
        },
    ],
    "Hardware Options": [
        {
            "name": "Lock Type",
            "data_type": "selection",
            "required": True,
            "ui_component": "radio",
            "description": "Locking mechanism",
            "help_text": "Security level varies by lock type",
        },
        {
            "name": "Handle Style",
            "data_type": "selection",
            "required": True,
            "ui_component": "dropdown",
            "description": "Handle design",
            "help_text": "Choose style to match decor",
        },
        {
            "name": "Hinge Type",
            "data_type": "selection",
            "required": False,
            "ui_component": "radio",
            "description": "Hinge mechanism",
            "help_text": "Affects opening direction and durability",
        },
        {
            "name": "Hardware Finish",
            "data_type": "selection",
            "required": False,
            "ui_component": "dropdown",
            "description": "Hardware finish color",
            "help_text": "Match or contrast with frame",
        },
    ],
    "Dimensions": [
        {
            "name": "Width",
            "data_type": "number",
            "required": True,
            "ui_component": "input",
            "description": "Width in inches",
            "help_text": "Measure the rough opening",
        },
        {
            "name": "Height",
            "data_type": "number",
            "required": True,
            "ui_component": "input",
            "description": "Height in inches",
            "help_text": "Measure from sill to header",
        },
        {
            "name": "Depth",
            "data_type": "number",
            "required": False,
            "ui_component": "input",
            "description": "Depth in inches",
            "help_text": "Wall thickness for installation",
        },
    ],
    "Energy Features": [
        {
            "name": "Insulation Level",
            "data_type": "selection",
            "required": False,
            "ui_component": "radio",
            "description": "Insulation rating",
            "help_text": "Higher rating = better energy efficiency",
        },
        {
            "name": "Weather Stripping",
            "data_type": "selection",
            "required": False,
            "ui_component": "radio",
            "description": "Weather seal type",
            "help_text": "Prevents air infiltration",
        },
        {
            "name": "Energy Star Certified",
            "data_type": "boolean",
            "required": False,
            "ui_component": "checkbox",
            "description": "Energy Star certification",
            "help_text": "May qualify for tax credits",
        },
    ],
    "Security Features": [
        {
            "name": "Security Rating",
            "data_type": "selection",
            "required": False,
            "ui_component": "radio",
            "description": "Security level",
            "help_text": "Higher rating = better protection",
        },
        {
            "name": "Reinforced Frame",
            "data_type": "boolean",
            "required": False,
            "ui_component": "checkbox",
            "description": "Steel-reinforced frame",
            "help_text": "Increases break-in resistance",
        },
        {
            "name": "Impact Resistant",
            "data_type": "boolean",
            "required": False,
            "ui_component": "checkbox",
            "description": "Impact-resistant glass",
            "help_text": "Required in hurricane zones",
        },
    ],
    "Aesthetic Options": [
        {
            "name": "Grid Pattern",
            "data_type": "selection",
            "required": False,
            "ui_component": "dropdown",
            "description": "Decorative grid pattern",
            "help_text": "Colonial, prairie, or custom",
        },
        {
            "name": "Trim Style",
            "data_type": "selection",
            "required": False,
            "ui_component": "dropdown",
            "description": "Interior trim style",
            "help_text": "Matches interior decor",
        },
    ],
    "Installation Options": [
        {
            "name": "Installation Method",
            "data_type": "selection",
            "required": True,
            "ui_component": "radio",
            "description": "Installation type",
            "help_text": "New construction vs retrofit",
        },
        {
            "name": "Professional Installation",
            "data_type": "boolean",
            "required": False,
            "ui_component": "checkbox",
            "description": "Include professional installation",
            "help_text": "Recommended for warranty coverage",
        },
    ],
}

# Option Templates (Level 2+ - Selectable choices)
OPTIONS = {
    "Frame Material": [
        {
            "name": "Aluminum",
            "price_range": (40.00, 70.00),
            "weight_range": (2.00, 3.50),
            "description": "Durable aluminum frame",
            "help_text": "Best for coastal areas, corrosion resistant",
        },
        {
            "name": "Vinyl",
            "price_range": (25.00, 45.00),
            "weight_range": (1.50, 2.50),
            "description": "Low-maintenance vinyl frame",
            "help_text": "Energy efficient and affordable",
        },
        {
            "name": "Wood",
            "price_range": (100.00, 180.00),
            "weight_range": (3.00, 5.00),
            "description": "Premium wood frame",
            "help_text": "Classic look with natural insulation",
        },
        {
            "name": "Fiberglass",
            "price_range": (80.00, 140.00),
            "weight_range": (2.50, 4.00),
            "description": "High-performance fiberglass",
            "help_text": "Strongest and most durable",
        },
        {
            "name": "Composite",
            "price_range": (60.00, 100.00),
            "weight_range": (2.00, 3.50),
            "description": "Wood-composite blend",
            "help_text": "Wood look without maintenance",
        },
    ],
    "Frame Color": [
        {"name": "White", "price_range": (0.00, 0.00), "weight_range": (0.00, 0.00)},
        {"name": "Black", "price_range": (15.00, 30.00), "weight_range": (0.00, 0.00)},
        {"name": "Bronze", "price_range": (20.00, 35.00), "weight_range": (0.00, 0.00)},
        {"name": "Beige", "price_range": (10.00, 20.00), "weight_range": (0.00, 0.00)},
        {"name": "Gray", "price_range": (15.00, 25.00), "weight_range": (0.00, 0.00)},
        {"name": "Custom Color", "price_range": (50.00, 100.00), "weight_range": (0.00, 0.00)},
    ],
    "Frame Finish": [
        {"name": "Matte", "price_range": (0.00, 0.00), "weight_range": (0.00, 0.00)},
        {"name": "Satin", "price_range": (20.00, 40.00), "weight_range": (0.00, 0.00)},
        {"name": "Gloss", "price_range": (30.00, 50.00), "weight_range": (0.00, 0.00)},
        {"name": "Textured", "price_range": (25.00, 45.00), "weight_range": (0.00, 0.00)},
    ],
    "Pane Configuration": [
        {
            "name": "Single Pane",
            "price_range": (0.00, 0.00),
            "weight_range": (2.50, 4.00),
            "description": "Single pane glass",
            "help_text": "Basic option, less insulation",
        },
        {
            "name": "Double Pane",
            "price_range": (70.00, 120.00),
            "weight_range": (5.00, 7.50),
            "description": "Double pane insulated glass",
            "help_text": "Good energy efficiency",
        },
        {
            "name": "Triple Pane",
            "price_range": (160.00, 250.00),
            "weight_range": (7.50, 11.00),
            "description": "Triple pane maximum insulation",
            "help_text": "Best energy efficiency, quieter",
        },
    ],
    "Glass Type": [
        {"name": "Clear", "price_range": (0.00, 0.00), "weight_range": (0.00, 0.00)},
        {"name": "Tempered", "price_range": (40.00, 70.00), "weight_range": (0.50, 1.00)},
        {"name": "Laminated", "price_range": (60.00, 100.00), "weight_range": (1.00, 2.00)},
        {"name": "Low-Iron", "price_range": (50.00, 90.00), "weight_range": (0.00, 0.00)},
        {"name": "Obscured", "price_range": (30.00, 60.00), "weight_range": (0.00, 0.00)},
    ],
    "Glass Coating": [
        {
            "name": "Low-E Coating",
            "price_range": (40.00, 70.00),
            "weight_range": (0.00, 0.00),
            "description": "Low-emissivity coating",
            "help_text": "Reflects heat, improves energy efficiency",
        },
        {
            "name": "UV Protection",
            "price_range": (30.00, 55.00),
            "weight_range": (0.00, 0.00),
            "description": "UV protection coating",
            "help_text": "Protects furniture from fading",
        },
        {
            "name": "Self-Cleaning",
            "price_range": (80.00, 130.00),
            "weight_range": (0.00, 0.00),
            "description": "Hydrophobic self-cleaning coating",
            "help_text": "Reduces maintenance",
        },
    ],
    "Tint Level": [
        {"name": "No Tint", "price_range": (0.00, 0.00), "weight_range": (0.00, 0.00)},
        {"name": "Light Tint", "price_range": (25.00, 45.00), "weight_range": (0.00, 0.00)},
        {"name": "Medium Tint", "price_range": (35.00, 60.00), "weight_range": (0.00, 0.00)},
        {"name": "Dark Tint", "price_range": (45.00, 75.00), "weight_range": (0.00, 0.00)},
    ],
    "Lock Type": [
        {"name": "Standard Lock", "price_range": (0.00, 0.00), "weight_range": (0.50, 1.00)},
        {"name": "Multi-Point Lock", "price_range": (60.00, 120.00), "weight_range": (1.50, 2.50)},
        {"name": "Smart Lock", "price_range": (150.00, 300.00), "weight_range": (1.00, 2.00)},
        {"name": "Deadbolt", "price_range": (40.00, 80.00), "weight_range": (1.00, 1.50)},
    ],
    "Handle Style": [
        {"name": "Lever", "price_range": (20.00, 50.00), "weight_range": (0.30, 0.60)},
        {"name": "Knob", "price_range": (15.00, 40.00), "weight_range": (0.25, 0.50)},
        {"name": "Pull", "price_range": (30.00, 70.00), "weight_range": (0.40, 0.80)},
        {"name": "Touchless", "price_range": (100.00, 200.00), "weight_range": (0.50, 1.00)},
    ],
    "Hinge Type": [
        {"name": "Standard Hinge", "price_range": (0.00, 0.00), "weight_range": (0.50, 1.00)},
        {"name": "Heavy-Duty Hinge", "price_range": (30.00, 60.00), "weight_range": (1.00, 2.00)},
        {"name": "Concealed Hinge", "price_range": (50.00, 100.00), "weight_range": (0.80, 1.50)},
    ],
    "Hardware Finish": [
        {"name": "Brushed Nickel", "price_range": (0.00, 0.00), "weight_range": (0.00, 0.00)},
        {"name": "Oil-Rubbed Bronze", "price_range": (20.00, 40.00), "weight_range": (0.00, 0.00)},
        {"name": "Polished Chrome", "price_range": (15.00, 30.00), "weight_range": (0.00, 0.00)},
        {"name": "Matte Black", "price_range": (25.00, 45.00), "weight_range": (0.00, 0.00)},
    ],
    "Insulation Level": [
        {"name": "Standard", "price_range": (0.00, 0.00), "weight_range": (0.00, 0.00)},
        {"name": "Enhanced", "price_range": (50.00, 90.00), "weight_range": (1.00, 2.00)},
        {"name": "Maximum", "price_range": (100.00, 180.00), "weight_range": (2.00, 3.50)},
    ],
    "Weather Stripping": [
        {"name": "Standard Foam", "price_range": (0.00, 0.00), "weight_range": (0.10, 0.20)},
        {"name": "Silicone", "price_range": (20.00, 40.00), "weight_range": (0.15, 0.30)},
        {"name": "Magnetic", "price_range": (40.00, 70.00), "weight_range": (0.30, 0.50)},
    ],
    "Security Rating": [
        {"name": "Standard", "price_range": (0.00, 0.00), "weight_range": (0.00, 0.00)},
        {"name": "Enhanced", "price_range": (80.00, 150.00), "weight_range": (2.00, 4.00)},
        {"name": "Maximum", "price_range": (200.00, 400.00), "weight_range": (4.00, 7.00)},
    ],
    "Grid Pattern": [
        {"name": "No Grid", "price_range": (0.00, 0.00), "weight_range": (0.00, 0.00)},
        {"name": "Colonial", "price_range": (40.00, 80.00), "weight_range": (0.50, 1.00)},
        {"name": "Prairie", "price_range": (45.00, 90.00), "weight_range": (0.60, 1.20)},
        {"name": "Custom", "price_range": (80.00, 160.00), "weight_range": (0.80, 1.50)},
    ],
    "Trim Style": [
        {"name": "Standard", "price_range": (0.00, 0.00), "weight_range": (0.00, 0.00)},
        {"name": "Colonial", "price_range": (30.00, 60.00), "weight_range": (1.00, 2.00)},
        {"name": "Craftsman", "price_range": (40.00, 80.00), "weight_range": (1.50, 2.50)},
        {"name": "Modern", "price_range": (35.00, 70.00), "weight_range": (0.80, 1.50)},
    ],
    "Installation Method": [
        {"name": "New Construction", "price_range": (0.00, 0.00), "weight_range": (0.00, 0.00)},
        {"name": "Retrofit", "price_range": (50.00, 100.00), "weight_range": (0.00, 0.00)},
        {"name": "Pocket Replacement", "price_range": (30.00, 70.00), "weight_range": (0.00, 0.00)},
    ],
}

# Boolean options (for checkbox attributes)
BOOLEAN_OPTIONS = [
    {
        "name": "Yes",
        "price_range": (50.00, 150.00),
        "weight_range": (0.00, 2.00),
    },
    {
        "name": "No",
        "price_range": (0.00, 0.00),
        "weight_range": (0.00, 0.00),
    },
]

# Price impact types distribution (for randomization)
PRICE_IMPACT_TYPES = ["fixed", "percentage", "formula"]
PRICE_IMPACT_TYPE_WEIGHTS = [0.7, 0.2, 0.1]  # 70% fixed, 20% percentage, 10% formula

# Formula templates for dynamic pricing
PRICE_FORMULAS = [
    "width * height * {factor}",
    "(width + height) * 2 * {factor}",
    "base_price * {factor}",
    "area * {factor}",
    "width * height * depth * {factor}",
]

WEIGHT_FORMULAS = [
    "area * {factor}",
    "width * height * {factor}",
    "(width + height) * {factor}",
    "volume * {factor}",
]

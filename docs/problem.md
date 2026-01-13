# Current Problem:

- Our data is based on what we enter as code, but data entry personnel are not familiar with coding.
- The core problem in the profile page lies with its input field options—these options are just text without any relationships. As shown in the image, the system does not enforce a hierarchical relationship.
- We need a new page called "Relations" that will allow data entry for specific values and record them. Each record constructs a new path in the hierarchy.
    - To clarify: the hierarchy structure is solid and fixed, but the option dependencies create dynamically constructed paths. The hierarchy dependency is:
    - **[Company] → [Material] → [Opening_system] → [System_series] → [Colors]**
    - Note: There is an additional table that does not affect the dependency but should also be saved:

```sql
-- Unit Types table
CREATE TABLE unit_types (
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    image_url VARCHAR(255),
    -- created_at is used internally for auditing purposes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

```

- Their data fields:

```sql
-- Materials table
CREATE TABLE materials (
    name VARCHAR(50) UNIQUE NOT NULL,
    image_url VARCHAR(255),
    price_from NUMERIC(10,2),
    density NUMERIC(10,2),
    -- created_at is used internally for auditing purposes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Colors table
CREATE TABLE colors (
    picture_url VARCHAR(255) NOT NULL,
    name VARCHAR(50) UNIQUE NOT NULL,
    code VARCHAR(15),
    has_lamination BOOLEAN DEFAULT FALSE NOT NULL,
    -- created_at is used internally for auditing purposes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Opening Systems table
CREATE TABLE opening_systems (
    name VARCHAR(100) NOT NULL,
    description TEXT,
    image_url VARCHAR(255),
    price_from NUMERIC(10,2) CHECK (price_from >= 0),
    -- created_at is used internally for auditing purposes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Companies table
CREATE TABLE companies (
    name VARCHAR(50) UNIQUE NOT NULL,
    logo_url VARCHAR(255),
    price_from NUMERIC(10,2),
    -- created_at is used internally for auditing purposes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System Series table
CREATE TABLE system_series (
    name VARCHAR(100) UNIQUE NOT NULL,
    image_url VARCHAR(255),
    width NUMERIC(10,2),
    number_of_chambers INT CHECK (number_of_chambers > 0),
    u_value NUMERIC(5,2),
    number_of_seals INT CHECK (number_of_seals > 0),
    characteristics VARCHAR(50),
    price_from NUMERIC(10,2),
    -- created_at is used internally for auditing purposes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

```

## The Flow:

Data entry personnel enter data into these fields, which then updates the option hierarchy on the profile-entry page.

**Example of Recorded Paths:**

1. Komben → UPVC → Casement → K700 → White
2. Komben → UPVC → Casement → K600 → Red
3. Komben → Aluminum → Casement → K701 → Green
4. Komben → Aluminum → Sliding → K800 → Blue

**How It Works on the Profile Page:**

When a user selects **Komben** as the company, the Material select box should display only: **[UPVC | Aluminum]**

- If the user then selects **UPVC**, the Opening System select box shows: **[Casement]**
    - Then selecting **Casement** shows System Series: **[K700, K600]**
        - Then selecting **K700** shows Colors: **[White]**
- If the user then selects **UPVC**, the Opening System select box shows: **[Casement]**
    - Then selecting **Casement** shows System Series: **[K700]**
        - Then selecting **K700** shows Colors: **[White]**
- If the user selects **Aluminum** instead, the Opening System select box shows: **[Casement | Sliding]**
    - Selecting **Casement** shows System Series: **[K701]**
        - Then **K701** shows Colors: **[Green]**
    - Selecting **Sliding** shows System Series: **[K800]**
        - Then **K800** shows Colors: **[Blue]**

**Key Point:** Each dropdown only displays options that exist in the recorded paths, ensuring data integrity and preventing invalid combinations.
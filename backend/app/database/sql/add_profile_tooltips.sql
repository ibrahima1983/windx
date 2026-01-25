-- Update Attribute Node Descriptions for Profile Entry Tooltips
-- This script adds comprehensive, helpful tooltip content to attribute nodes

-- Manufacturing Type: UPVC Profiles (ID: 475)

-- Basic Information Fields
UPDATE attribute_nodes 
SET description = 'A unique identifier for this profile.<br><br><strong>Examples:</strong><br>• ''Standard Casement Window''<br>• ''Premium Sliding Door''<br>• ''Economy Frame Profile''<br><br><strong>Tip:</strong> Use descriptive names that clearly identify the product type and variant.',
    help_text = 'This name will be used in reports, quotes, and inventory listings. Make it descriptive enough to distinguish between similar profiles.'
WHERE name = 'name' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'The category of this profile component.<br><br><strong>Options:</strong><br>• <strong>Frame</strong> - Main structural component that holds the glass<br>• <strong>Sash</strong> - Movable window panel<br>• <strong>Mullion</strong> - Vertical or horizontal divider<br>• <strong>Glazing Bead</strong> - Strip that holds glass in place<br>• <strong>Track</strong> - Sliding mechanism component',
    help_text = 'Select the type that best describes this profile''s function in the window or door assembly.'
WHERE name = 'type' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'The manufacturer or supplier of this profile system.<br><br><strong>Use:</strong><br>• Select from your database of approved suppliers<br>• Affects pricing, availability, and compatibility<br>• Used for inventory tracking and ordering<br><br><strong>Note:</strong> Different companies may have incompatible profile systems.',
    help_text = 'Ensure all components in a project use compatible systems from the same manufacturer.'
WHERE name = 'company' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'The primary material composition of the profile.<br><br><strong>Common Options:</strong><br>• <strong>UPVC</strong> - Durable, low-maintenance plastic (most common)<br>• <strong>Aluminum</strong> - Strong, corrosion-resistant metal<br>• <strong>Wood</strong> - Traditional, natural material<br>• <strong>Composite</strong> - Combination of materials<br><br><strong>Properties:</strong><br>• Affects thermal performance<br>• Determines maintenance requirements<br>• Impacts pricing',
    help_text = 'UPVC is the most popular choice for residential applications due to its durability and low maintenance.'
WHERE name = 'material' AND manufacturing_type_id = 475;

-- System Specifications
UPDATE attribute_nodes 
SET description = 'The window or door opening mechanism type.<br><br><strong>Common Types:</strong><br>• <strong>Casement</strong> - Hinged window that opens outward<br>• <strong>Sliding</strong> - Horizontal sliding panels<br>• <strong>Tilt & Turn</strong> - Dual-action opening<br>• <strong>Fixed</strong> - Non-opening window<br>• <strong>Awning</strong> - Top-hinged, opens outward<br><br><strong>Selection Criteria:</strong><br>• Space availability<br>• Ventilation needs<br>• Ease of cleaning',
    help_text = 'The opening system affects hardware requirements, pricing, and installation complexity.'
WHERE name = 'opening_system' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'The specific profile system series from the manufacturer.<br><br><strong>Examples:</strong><br>• Kom700 - Standard residential series<br>• Kom701 - Enhanced thermal performance<br>• Kom800 - Premium commercial series<br><br><strong>Series Differences:</strong><br>• Chamber count (thermal efficiency)<br>• Wall thickness (strength)<br>• Glass capacity<br>• Price point',
    help_text = 'Higher series numbers typically indicate better performance and higher cost. Verify compatibility with other components.'
WHERE name = 'system_series' AND manufacturing_type_id = 475;

-- Dimensions
UPDATE attribute_nodes 
SET description = 'The width of the profile cross-section in millimeters.<br><br><strong>Measurement:</strong><br>• Measure the actual profile width<br>• Include any flanges or extensions<br>• Exclude gaskets and seals<br><br><strong>Common Widths:</strong><br>• Frame profiles: 60-90mm<br>• Sash profiles: 50-70mm<br>• Mullions: 40-60mm<br><br><strong>Impact:</strong><br>• Affects glass capacity<br>• Determines thermal performance<br>• Influences material cost',
    help_text = 'Wider profiles generally provide better insulation but cost more. Verify compatibility with glass thickness.'
WHERE name = 'width' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'The total width including built-in flyscreen track (if applicable).<br><br><strong>When to Use:</strong><br>• Only for frames with integrated flyscreen<br>• Includes the main profile + flyscreen track<br>• Measured in millimeters<br><br><strong>Calculation:</strong><br>• Total Width = Profile Width + Flyscreen Track Width<br><br><strong>Note:</strong> Leave empty if no flyscreen track is present.',
    help_text = 'This dimension is critical for accurate material ordering and pricing calculations.'
WHERE name = 'total_width' AND manufacturing_type_id = 475;

-- Heights
UPDATE attribute_nodes 
SET description = 'The front-facing height of the profile in millimeters.<br><br><strong>Measurement:</strong><br>• Measure from the bottom edge to top edge<br>• Front side (exterior-facing)<br>• Exclude any overlapping sections<br><br><strong>Common Heights:</strong><br>• Standard frames: 60-80mm<br>• Deep frames: 80-120mm<br><br><strong>Affects:</strong><br>• Visual appearance<br>• Structural strength<br>• Installation depth',
    help_text = 'Front height affects the visible frame size from outside. Ensure it matches architectural requirements.'
WHERE name = 'front_height' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'The rear-facing height of the profile in millimeters.<br><br><strong>Measurement:</strong><br>• Measure from bottom to top on interior side<br>• May differ from front height in stepped profiles<br>• Exclude gaskets and seals<br><br><strong>Purpose:</strong><br>• Determines interior appearance<br>• Affects installation clearance<br>• Impacts thermal bridge calculations',
    help_text = 'Rear height is important for interior aesthetics and proper installation in wall openings.'
WHERE name = 'rear_height' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'The vertical space available for glass installation in millimeters.<br><br><strong>Calculation:</strong><br>• Total frame height minus rebate depths<br>• Accounts for glazing beads and gaskets<br>• Determines maximum glass thickness<br><br><strong>Critical For:</strong><br>• Glass ordering<br>• Thermal performance<br>• Acoustic insulation<br><br><strong>Typical Values:</strong><br>• Single glazing: 4-6mm<br>• Double glazing: 20-28mm<br>• Triple glazing: 36-44mm',
    help_text = 'Ensure glazing height accommodates your chosen glass unit thickness plus necessary clearances.'
WHERE name = 'glazing_height' AND manufacturing_type_id = 475;

-- Pricing and Discounts
UPDATE attribute_nodes 
SET description = 'Percentage discount applied to UPVC profile pricing.<br><br><strong>Usage:</strong><br>• Standard discount: 15-25%<br>• Volume discount: up to 40%<br>• Promotional discount: varies<br><br><strong>Application:</strong><br>• Applied to base profile price<br>• Before other calculations<br>• Affects final quote pricing<br><br><strong>Example:</strong><br>• Base price: $100/meter<br>• 20% discount: Final = $80/meter',
    help_text = 'This discount is typically negotiated with suppliers based on volume commitments. Update regularly based on current agreements.'
WHERE name = 'upvc_profile_discount' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'The cost per linear meter of this profile in your local currency.<br><br><strong>Includes:</strong><br>• Base material cost<br>• Manufacturing overhead<br>• Supplier markup<br><br><strong>Excludes:</strong><br>• Installation labor<br>• Hardware and accessories<br>• Glass and glazing<br><br><strong>Note:</strong> This is the list price before any discounts are applied.',
    help_text = 'Update this price regularly to reflect current supplier pricing. Use for cost estimation and quoting.'
WHERE name = 'price_per_meter' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'The total price for a complete beam/length of this profile.<br><br><strong>Use When:</strong><br>• Profiles are sold in fixed lengths<br>• Bulk pricing applies<br>• Pre-cut beams are ordered<br><br><strong>Calculation:</strong><br>• Price per Beam = (Length × Price/Meter) - Volume Discount<br><br><strong>Alternative:</strong> Leave empty if pricing is strictly per meter.',
    help_text = 'Some suppliers offer better pricing for full beams. Compare with per-meter pricing to find the best value.'
WHERE name = 'price_per_beam' AND manufacturing_type_id = 475;

-- Technical Specifications
UPDATE attribute_nodes 
SET description = 'The weight of the profile per linear meter in kilograms.<br><br><strong>Purpose:</strong><br>• Shipping cost calculations<br>• Structural load analysis<br>• Hardware sizing<br>• Installation planning<br><br><strong>Typical Values:</strong><br>• Light profiles: 0.5-1.0 kg/m<br>• Standard profiles: 1.0-2.0 kg/m<br>• Heavy profiles: 2.0-4.0 kg/m<br><br><strong>Factors:</strong><br>• Profile width and height<br>• Wall thickness<br>• Number of chambers',
    help_text = 'Heavier profiles generally indicate thicker walls and better structural performance but increase shipping costs.'
WHERE name = 'weight_per_meter' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'Steel reinforcement options for enhanced structural strength.<br><br><strong>When Required:</strong><br>• Large window/door sizes<br>• High wind load areas<br>• Commercial applications<br>• Security requirements<br><br><strong>Options:</strong><br>• Standard U-channel steel<br>• Heavy-duty box section<br>• Galvanized for corrosion resistance<br>• Custom profiles for special applications<br><br><strong>Selection:</strong> Choose from your steel database based on profile cavity size and load requirements.',
    help_text = 'Steel reinforcement significantly increases strength and rigidity. Required by building codes for openings above certain sizes.'
WHERE name = 'reinforcement_steel' AND manufacturing_type_id = 475;

-- Specialized Features
UPDATE attribute_nodes 
SET description = 'Indicates if this profile is designed for renovation/retrofit applications.<br><br><strong>Options:</strong><br>• <strong>Yes</strong> - Designed for existing window replacement<br>• <strong>No</strong> - New construction only<br>• <strong>N/A</strong> - Not applicable to this profile type<br><br><strong>Renovation Features:</strong><br>• Reduced installation depth<br>• Mounting flanges for existing frames<br>• Simplified installation process<br>• May have different pricing',
    help_text = 'Renovation profiles are specifically designed to fit into existing window openings with minimal structural modification.'
WHERE name = 'renovation' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'Indicates if this frame includes an integrated flyscreen track.<br><br><strong>Purpose:</strong><br>• Allows installation of retractable flyscreen<br>• No additional frame modification needed<br>• Cleaner aesthetic than add-on screens<br><br><strong>Considerations:</strong><br>• Increases total frame width<br>• Adds to material cost<br>• Requires compatible flyscreen system<br><br><strong>When to Use:</strong><br>• Residential applications<br>• Areas with insects<br>• Customer preference for screens',
    help_text = 'Built-in flyscreen tracks are popular in residential applications. Ensure you specify the correct track height.'
WHERE name = 'builtin_flyscreen_track' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'The height of the integrated flyscreen track in millimeters.<br><br><strong>Measurement:</strong><br>• Vertical dimension of the track channel<br>• Determines compatible flyscreen systems<br>• Affects total frame width<br><br><strong>Common Heights:</strong><br>• Standard: 15-20mm<br>• Heavy-duty: 20-25mm<br><br><strong>Note:</strong> Only applicable when "Built-in Flyscreen Track" is enabled.',
    help_text = 'Match this height to your flyscreen system specifications. Incorrect height will prevent proper flyscreen installation.'
WHERE name = 'flyscreen_track_height' AND manufacturing_type_id = 475;

-- Color Options
UPDATE attribute_nodes 
SET description = 'Available color options for this profile.<br><br><strong>Standard Colors:</strong><br>• White (RAL 9016) - Most common<br>• Anthracite Grey (RAL 7016) - Modern aesthetic<br>• Brown/Woodgrain - Traditional look<br>• Custom RAL colors - Premium option<br><br><strong>Finish Types:</strong><br>• Solid color<br>• Woodgrain texture<br>• Metallic finish<br><br><strong>Pricing Impact:</strong><br>• White: Base price<br>• Standard colors: +10-15%<br>• Woodgrain: +20-30%<br>• Custom RAL: +30-50%',
    help_text = 'Color availability varies by manufacturer and series. Confirm availability before quoting to customers.'
WHERE name = 'colours' AND manufacturing_type_id = 475;

-- Advanced Measurements
UPDATE attribute_nodes 
SET description = 'The overlap dimension where sash meets frame in millimeters.<br><br><strong>Purpose:</strong><br>• Ensures weather-tight seal<br>• Affects visual appearance<br>• Determines gasket requirements<br><br><strong>Typical Values:</strong><br>• Standard overlap: 8-12mm<br>• Enhanced seal: 12-16mm<br><br><strong>Note:</strong> Only applicable to sash profiles. Leave empty for other profile types.',
    help_text = 'Proper sash overlap is critical for weather performance. Too little causes leaks, too much causes operation issues.'
WHERE name = 'sash_overlap' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'Horizontal clearance required for flying mullion operation in millimeters.<br><br><strong>What is a Flying Mullion?</strong><br>• Removable vertical divider<br>• Allows full opening width<br>• Common in French doors<br><br><strong>Clearance Purpose:</strong><br>• Ensures smooth operation<br>• Prevents binding<br>• Allows for thermal expansion<br><br><strong>Typical Values:</strong> 3-6mm per side',
    help_text = 'Flying mullions require precise clearances. Too tight causes binding, too loose affects weather sealing.'
WHERE name = 'flying_mullion_horizontal_clearance' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'Vertical clearance required for flying mullion operation in millimeters.<br><br><strong>Purpose:</strong><br>• Allows vertical movement during operation<br>• Accommodates thermal expansion<br>• Prevents jamming<br><br><strong>Typical Values:</strong> 2-5mm<br><br><strong>Critical For:</strong><br>• Smooth operation<br>• Long-term durability<br>• Weather performance',
    help_text = 'Vertical clearance must account for building settlement and thermal expansion. Follow manufacturer specifications.'
WHERE name = 'flying_mullion_vertical_clearance' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'The thickness of steel reinforcement material in millimeters.<br><br><strong>Common Thicknesses:</strong><br>• Light-duty: 1.0-1.5mm<br>• Standard: 1.5-2.0mm<br>• Heavy-duty: 2.0-3.0mm<br><br><strong>Selection Criteria:</strong><br>• Window/door size<br>• Wind load requirements<br>• Building code requirements<br>• Security needs<br><br><strong>Impact:</strong><br>• Thicker = stronger but heavier<br>• Affects profile weight<br>• Influences pricing',
    help_text = 'Steel thickness must meet local building codes for the specific application. Consult structural calculations for large openings.'
WHERE name = 'steel_material_thickness' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'Additional height for renovation frame profiles in millimeters.<br><br><strong>Purpose:</strong><br>• Accounts for existing frame overlap<br>• Ensures proper fit in renovation applications<br>• Affects total frame dimensions<br><br><strong>Typical Values:</strong> 10-30mm<br><br><strong>Note:</strong> Only applicable when "Renovation" is set to "Yes". Leave empty for new construction profiles.',
    help_text = 'Renovation height compensates for the existing frame that remains in place. Measure the existing frame carefully.'
WHERE name = 'renovation_height' AND manufacturing_type_id = 475;

UPDATE attribute_nodes 
SET description = 'The undercut height dimension for glazing bead profiles in millimeters.<br><br><strong>What is Glazing Undercut?</strong><br>• Recessed area that holds glass edge<br>• Provides secure glass retention<br>• Allows for glazing gasket<br><br><strong>Purpose:</strong><br>• Ensures proper glass seating<br>• Affects glazing capacity<br>• Determines gasket size<br><br><strong>Note:</strong> Only applicable to glazing bead profiles.',
    help_text = 'Glazing undercut must match the glass edge thickness and gasket requirements. Critical for weather-tight installation.'
WHERE name = 'glazing_undercut_height' AND manufacturing_type_id = 475;

-- Product Code
UPDATE attribute_nodes 
SET description = 'Unique product code or SKU for this profile.<br><br><strong>Format:</strong><br>• Manufacturer code + Series + Variant<br>• Example: KOM700-FR-60-WH<br><br><strong>Purpose:</strong><br>• Inventory tracking<br>• Order processing<br>• Cross-referencing with supplier catalogs<br><br><strong>Best Practice:</strong> Use manufacturer''s official code when available for accurate ordering.',
    help_text = 'Product codes ensure you order the exact profile needed. Verify codes with supplier catalogs before placing orders.'
WHERE name = 'code' AND manufacturing_type_id = 475;

-- Length/Beam
UPDATE attribute_nodes 
SET description = 'The standard length of beam/bar for this profile in meters.<br><br><strong>Common Lengths:</strong><br>• Standard: 6 meters<br>• Long: 7-8 meters<br>• Custom: Variable<br><br><strong>Considerations:</strong><br>• Transportation limitations<br>• Cutting waste<br>• Storage requirements<br>• Pricing (longer may be more economical)<br><br><strong>Note:</strong> Some suppliers only sell in specific lengths.',
    help_text = 'Longer beams reduce waste for large projects but may have higher shipping costs. Calculate optimal length based on your typical project sizes.'
WHERE name = 'length_of_beam' AND manufacturing_type_id = 475;

-- Image/Documentation
UPDATE attribute_nodes 
SET description = 'Profile cross-section image or technical drawing.<br><br><strong>Recommended Format:</strong><br>• SVG (scalable, best quality)<br>• PNG (good for photos)<br>• JPG (acceptable)<br><br><strong>Content:</strong><br>• Cross-section view<br>• Dimension callouts<br>• Chamber configuration<br>• Reinforcement cavity<br><br><strong>Size:</strong> Maximum 800x400px for optimal display',
    help_text = 'A clear cross-section image helps with profile selection and customer presentations. Include dimension markers for reference.'
WHERE name = 'pic' AND manufacturing_type_id = 475;

COMMIT;

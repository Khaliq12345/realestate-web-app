

search_range_options = [
    "1_MONTH", "2_MONTH", 
    "3_MONTH", "6_MONTH", 
    "1_YEAR"
]

property_types = [
    'SFR',
    'MFR',
    'LAND',
    'CONDO',
    'MOBILE',
    'OTHER'
]

mls_statuses = [
    'mls_active',
    'mls_pending',
    'mls_cancelled'
]

filters_part_1 = [
    'auction',
    'absentee_owner',
    'adjustable_rate',
    'cash_buyer',
    'corporate_owned',
    'death',
    'equity',
    'foreclosure',
    'free_clear',
    'high_equity',
    'inherited',
    'in_state_owner',
    'investor_buyer',
    'judgment',
    'out_of_state_owner',
    'pool',
    'pre_foreclosure',
    'private_lender',
    'reo',
    'tax_lien',
    'vacant'
]

min_max_inputs = [
    'mls_days_on_market',
    'baths',
    'beds',
    'building_size',
    'value',
    'year_built',
    'years_owned',
    #'last_update_date',
]

location_filters = [
    {"name": "Address", 'field': 'address', 'hint': ''},
    {"name": "State", 'field': 'state', 'hint': ''},
    {"name": "House", 'field': 'house', 'hint': ''},
    {"name": "Street", 'field': 'street', 'hint': ''},
    {"name": "City", 'field': 'city', 'hint': ''},
    {"name": "County", 'field': 'county', 'hint': ''},
    {"name": "Zip (comma-seperated)", 'field': 'zip', 'hint': 'must be 5 characters long'},
]

to_show_cols = [
    {"field":"address", "name": "Address"},
    {"field":"first_name", "name": "First Name"},
    {"field":"last_name", "name": "Last Name"},
    {"field":"property_type", "name": "Property Type"},
    {"field":"pre_foreclosure", "name": "Pre Forclosure"},
    {"field":"vacant", "name": "Vacant"},
    {"field":"owner_occupied", 'name': "Owner Occupied"}]


duplicate_message = """The following are duplicates properties (properties already in the database). 
                Select the property you want to remove,
                any property not selected will be updated automatically. If you wish to update or remove all duplicates,
                you can choose the (REMOVE ALL) or (UPDATE ALL) button below."""
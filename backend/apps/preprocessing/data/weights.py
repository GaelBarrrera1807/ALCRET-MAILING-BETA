WEIGHTS = {
    'threshold_relevant': 30,
    'threshold_high_priority': 60,
    'score_max': 100,
    'bonus_fleet_high': 15,
    'bonus_fleet_medium': 8,
    'bonus_size': 5,
    'bonus_complementary': 10,
    'bonus_commercial': 15,
    'penalty_exclusion': 0,
    'industry_match_high': 10,
    'industry_match_medium': 5,
    'industry_match_low': 2,
    'description_length_bonus': {
        'min_chars': 50,
        'points': 5,
    },
}

FIELD_KEYWORDS = {
    'name': [
        'nombre', 'razon social', 'razon social', 'denominacion',
        'denominacion', 'empresa', 'compania', 'compania',
        'titular', 'cliente', 'proveedor', 'prospecto',
        'name', 'company', 'business',
    ],
    'description': [
        'descripcion', 'descripcion', 'giro', 'actividad',
        'description', 'detalle', 'rubro', 'giro comercial',
        'giro de la empresa', 'giro comercial', 'actividad economica',
        'actividad economica', 'objeto social',
    ],
    'website': [
        'sitio', 'web', 'website', 'url', 'pagina', 'pagina', 'portal',
    ],
    'email': [
        'correo', 'email', 'mail', 'e-mail', 'electronico', 'electronico',
    ],
    'phone': [
        'telefono', 'telefono', 'phone', 'tel', 'celular',
        'movil', 'movil', 'contacto',
    ],
    'address': [
        'direccion', 'direccion', 'domicilio', 'calle', 'colonia',
        'address', 'ubicacion', 'ubicacion',
    ],
    'city': [
        'ciudad', 'municipio', 'poblacion', 'poblacion',
        'localidad', 'city', 'delegacion', 'delegacion',
    ],
    'state': [
        'estado', 'entidad federativa', 'provincia',
        'departamento', 'region', 'region', 'state',
    ],
    'country': ['pais', 'pais', 'country', 'nacion', 'nacion'],
    'rfc': ['rfc', 'registro federal', 'contribuyentes', 'tax_id', 'cif', 'nit'],
    'contact_name': [
        'nombre', 'representante', 'contacto', 'apellido', 'nombre completo',
    ],
    'contact_position': ['cargo', 'puesto', 'posicion', 'position', 'rol'],
    'contact_phone': ['telefono', 'telefono', 'celular', 'contacto'],
    'contact_email': ['correo', 'email', 'mail'],
}

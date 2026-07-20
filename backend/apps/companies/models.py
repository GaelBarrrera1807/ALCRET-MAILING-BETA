# Backwards-compat re-exports — models moved to apps.core.models
from apps.core.models import Sector, Product, Company, CompanyContact

__all__ = ['Sector', 'Product', 'Company', 'CompanyContact']

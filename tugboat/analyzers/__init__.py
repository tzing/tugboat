__all__ = [
    "check_resource_name",
    "report_duplicate_names",
]

from tugboat.analyzers.generic import report_duplicate_names
from tugboat.analyzers.kubernetes import check_resource_name

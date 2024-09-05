"""Tests."""

from schemathesis import experimental, models
from schemathesis.specs.openapi import loaders, schemas

from main import app

experimental.OPEN_API_3_1.enable()

schema: schemas.BaseOpenAPISchema = loaders.from_asgi('/openapi.json', app)


@schema.parametrize()
def test_schemathesis(case: models.Case):
    case.call_and_validate()

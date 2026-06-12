"""
Shared pytest configuration.

asyncio_mode = "auto" lets every async test function run without the
@pytest.mark.asyncio decorator.  Set in pytest.ini as well so the setting
is picked up by all test files in this directory.
"""
import pytest


# Nothing to configure beyond what pytest.ini sets, but this file must exist
# so pytest recognises the tests/ directory as a package root and so that
# future fixtures (e.g. a shared async DB session) have a home.

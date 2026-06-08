# Maintenance recipes for the ai-front-scaffold repo itself.
set shell := ["bash", "-cu"]

# Smoke-test the template by generating a throwaway project and running its tests
render-test:
    rm -rf /tmp/_aft && uvx copier copy --defaults --trust -d project_name="Smoke Test" . /tmp/_aft
    cd /tmp/_aft && uv run pytest -q

default:
    @just --list

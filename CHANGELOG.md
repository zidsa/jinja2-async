# Changelog

## 2026.1.30

- Fix `PrefixLoader.get_loader` type stub accidentally overriding parent implementation.
- Simplify `AsyncCodeGenerator.choose_async` to always choosing async_value.
- Fix codegen to properly await both `get_template` and `_get_default_module_async`/`make_module_async` for `{% import %}` and `{% from ... import %}` statements.

## 2026.1.12

- Fix hatchling packaging config.

## 2026.1.11

- Initial release.

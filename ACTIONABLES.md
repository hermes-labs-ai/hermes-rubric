# Actionables

Current as of the v1.1 portable-core release candidate.

## Release gate

- Run the full regression and the two adversarial tests.
- Run targeted lint on all v1.1 source, test, and example files; record unrelated baseline lint debt separately.
- Build wheel and sdist, inspect package contents, and test clean-wheel imports plus CLI version/help.
- Review the diff once for compatibility, coverage honesty, error semantics, and docs/code consistency.
- Publish GitHub and package-registry artifacts from the exact reviewed commit.
- Verify the public tag, release assets, and package installation independently.

## Post-release

- Implement the v1.2 evidence coverage engine described in `NEXT-UP.md`.
- Add framework adapters only after the public core and coverage contracts are stable.
- Make comparative or superiority claims only after a contemporaneous, reproducible baseline study.

Historical April planning and provisional GTM tasks were removed because they no longer describe current release state.

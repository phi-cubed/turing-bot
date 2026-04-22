# Turing @ DMF: testing interaction with mathrace

The test suite of `mathrace-interaction` is divided into four parts:
1. `unit` tests: these are basic tests for `mathrace-interaction`. They do not use journals of previous public competitions, and do not require **Turing** to be available.
2. `functional` tests: these tests check `mathrace-interaction` against a set of journals derived from previous public competitions (e.g., Disfida Matematica in Brescia). They use journals stored in `data`, but do not require **Turing** to be available.
3. `integration` tests: these tests check the integration between `mathrace-interaction` and **Turing**. They use journals stored in `data`, and require **Turing** to be available. Due to the large processing time, these tests use by default only a subset of the journals stored in `data`: invoke `pytest` with the command line option `--all-journals` to use all collected journals instead.

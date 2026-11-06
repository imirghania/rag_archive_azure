"""One file per job or app. A module never imports another module: it uses contracts, ports and the shared libraries
(messaging, artifactio) only. The rule is enforced by tests/test_architecture.py."""

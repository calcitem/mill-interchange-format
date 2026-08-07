# Security policy

MIF 1.0 parsers, resolvers, replay engines and release verifiers are in scope.
Reports should identify the affected signature/profile, exact commit or suite
digest, minimal input and the first failing validation stage.

Use GitHub private vulnerability reporting for the canonical repository when
available. Otherwise contact the repository maintainers without publishing
an exploit until a coordinated disclosure date is agreed. Public format or
documentation defects that do not create avoidable security risk may be filed
normally.

A security fix cannot silently reinterpret a frozen MIF signature. Follow the
compatibility and errata rules in `GOVERNANCE.md` and `mif-1.0.md`.

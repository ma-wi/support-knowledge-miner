# .NET and Visual Basic rules

Apply to `.sln`, `.vbproj`, `.vb`, and related .NET files.

- Use the repository SDK version and committed solution/project configuration.
- Keep analyzer settings strict where supported.
- Prefer explicit types and clear error handling in public or integration code.
- Do not weaken compiler warnings, analyzers, or tests to make a build pass.
- Use `dotnet format`, `dotnet test`, and `dotnet build` through repository scripts.
- Review NuGet packages for vulnerabilities, licensing, provenance, and transitive risk.

# Shell and PowerShell rules

Apply to Bash, POSIX shell, and PowerShell scripts.

- Enable strict and error-aware behavior appropriate to the shell.
- Quote variables and paths; do not construct commands from untrusted input.
- Avoid printing secrets or tokens.
- Make destructive operations explicit, bounded, and reversible where possible.
- Support non-interactive execution for CI.
- Use ShellCheck for shell scripts and PSScriptAnalyzer for PowerShell.
- Add tests with Bats or Pester when scripts contain meaningful logic.

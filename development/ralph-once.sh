#!/bin/bash


CLAUDE_CONFIG_DIR=~/.claude2 claude --permission-mode acceptEdits "@development/PRD.json @development/plan.md @development/progress.txt
1. Read the PRD and plan and progress files. \\
2. Find the next incomplete task and implement it. \\
3. run a code review subagent to review the changes, fix any issues you agree with.
4. Update progress.txt with what you did.\\
5. Commit your changes. \\
only do one thing at a time. if the prd is 100% complete, output <promise>COMPLETE</promise> "
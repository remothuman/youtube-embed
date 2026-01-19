#!/bin/bash

claude2 --permission-mode acceptEdits "@PRD
.md @progress
.txt @plan \\
.md\\
1. Read the PRD and plan and progress files. \\
2. Find the next incomplete task and implement it. \\
3. run a code review subagent to review the changes, fix any issues oyu agree with.
4. Commit your changes. \\
5. Update progress.txt with what you did. \\
only do one thing at a time. if the prd is 100% complete, output <promise>COMPLETE</promise> "
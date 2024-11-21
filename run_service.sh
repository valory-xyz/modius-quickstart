#!/bin/bash

# ------------------------------------------------------------------------------
#
#   Copyright 2024 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

if [ "$(git rev-parse --is-inside-work-tree)" = true ]
then
    # silently stop the existing service, if it exists
    chmod +x stop_service.sh && ./stop_service.sh > /dev/null 2>&1
    poetry install
    poetry run python run_service.py
else
    echo "$directory is not a git repo!"
    exit 1
fi

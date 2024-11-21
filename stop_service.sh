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
    poetry install
    poetry run python stop_service.py || echo "Stopping the deployment failed. Continuing with cleanup."

    # remove all containers with the name optimus, if they exist
    container_ids=$(docker ps -a -q --filter name=optimus)
    if [ -n "$container_ids" ]; then
      docker rm -f $container_ids
    fi

    # remove old deployments if they exist
    if ls .olas-modius/services/*/deployment 1> /dev/null 2>&1; then
      sudo rm -rf .olas-modius/services/*/deployment
    fi
else
    echo "$directory is not a git repo!"
    exit 1
fi

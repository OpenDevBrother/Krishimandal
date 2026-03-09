#!/bin/bash
export PATH=/home/ec2-user/.nvm/versions/node/v20.20.1/bin:$PATH
export CI=1
export EXPO_NO_TELEMETRY=1
cd /home/ec2-user/app/frontend
echo "Node: $(node --version)"
exec npx expo start --tunnel

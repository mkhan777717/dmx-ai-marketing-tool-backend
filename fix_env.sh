#!/bin/bash
cp .env .env.backup || cp .env.backup .env.real || true
for branch in feature/brand-kit feature/campaign-content feature/campaign-core feature/digital-asset-management feature/supabase-auth-rbac feature/workspace-management feature/project-setup main dev; do
  git checkout -f $branch
  if [ -f .env ]; then
    git rm -f .env
  fi
  cp .gitignore .gitignore.tmp || true
  cat << 'IGNORE' > .gitignore
# Environments
.env
.env.*
!.env.example
IGNORE
  git add .gitignore
  git commit -m "chore: remove .env and add .gitignore" || true
  git push origin $branch || true
done
cp .env.backup .env || true

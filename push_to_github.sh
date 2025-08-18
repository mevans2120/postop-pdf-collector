#!/bin/bash

echo "=========================================="
echo "Push PostOp PDF Collector to GitHub"
echo "=========================================="
echo ""
echo "First, create a new repository on GitHub:"
echo "1. Go to: https://github.com/new"
echo "2. Repository name: postop-pdf-collector"
echo "3. Description: Automated collection and analysis system for post-operative instruction PDFs"
echo "4. Make it Public"
echo "5. DON'T initialize with README, .gitignore, or license"
echo "6. Click 'Create repository'"
echo ""
read -p "Press Enter once you've created the repository..."

echo ""
read -p "Enter your GitHub username: " username

if [ -z "$username" ]; then
    echo "Username cannot be empty!"
    exit 1
fi

echo ""
echo "Adding remote origin..."
git remote add origin "https://github.com/${username}/postop-pdf-collector.git"

echo "Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Successfully pushed to GitHub!"
    echo "=========================================="
    echo ""
    echo "Your repository is now available at:"
    echo "https://github.com/${username}/postop-pdf-collector"
    echo ""
    echo "Next steps:"
    echo "1. Add a GitHub Actions workflow for CI/CD"
    echo "2. Configure GitHub Pages for documentation"
    echo "3. Set up branch protection rules"
    echo "4. Add collaborators if needed"
else
    echo ""
    echo "❌ Push failed. Please check your credentials and try again."
    echo ""
    echo "If you haven't set up authentication, you may need to:"
    echo "1. Create a Personal Access Token at https://github.com/settings/tokens"
    echo "2. Use the token as your password when prompted"
fi
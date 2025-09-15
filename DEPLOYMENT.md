# 🚀 GitHub Deployment Guide

This guide will help you deploy your yt-dlp wrapper project to GitHub.

## Prerequisites

- Git installed on your system
- GitHub account
- Repository ready for upload

## Step 1: Configure Git (First Time Only)

If you haven't used Git before, configure your identity:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Step 2: Create Initial Commit

The project is already initialized with Git. Create your first commit:

```bash
git commit -m "Initial commit: Complete yt-dlp wrapper with tests and documentation

- Interactive yt-dlp wrapper with smart archive system
- Support for MP3, MKV, and MP4 downloads  
- Automatic Firefox cookie detection for private playlists
- Comprehensive test suite with 48+ tests
- Complete documentation and examples
- GitHub Actions CI/CD workflow
- Windows-optimized with batch scripts
- Archive management and duplicate prevention
- M3U playlist generation
- VLC-optimized video settings"
```

## Step 3: Create GitHub Repository

1. Go to [GitHub.com](https://github.com)
2. Click the "+" button in the top right
3. Select "New repository"
4. Choose a repository name (e.g., `yt-dlp-wrapper`)
5. Add a description: "Interactive yt-dlp wrapper with smart features"
6. Make it **Public** (recommended for open source)
7. **Don't** initialize with README (we already have one)
8. Click "Create repository"

## Step 4: Connect Local Repository to GitHub

Replace `yourusername` with your actual GitHub username and `repository-name` with your chosen repository name:

```bash
git remote add origin https://github.com/yourusername/repository-name.git
git branch -M main
git push -u origin main
```

## Step 5: Update Repository URLs

After creating the GitHub repository, update the URLs in these files:

### README.md
- Replace `https://github.com/yourusername/yt-dlp-wrapper.git` with your actual repository URL
- Update all GitHub links throughout the document

### setup.py
- Update the `url` field with your repository URL
- Update `project_urls` with your repository URLs

### docs/CHANGELOG.md
- Update the release URL at the bottom

## Step 6: Verify Deployment

1. Visit your GitHub repository
2. Check that all files are uploaded
3. Verify the README displays correctly
4. Check that GitHub Actions are working (may take a few minutes)

## Step 7: Set Up GitHub Features

### Enable Discussions (Optional)
1. Go to repository Settings
2. Scroll to Features section
3. Enable Discussions

### Set Up Branch Protection (Recommended)
1. Go to Settings → Branches
2. Add rule for `main` branch
3. Enable "Require status checks to pass"
4. Select the test workflow

### Add Topics/Tags
1. Go to repository main page
2. Click the gear icon next to "About"
3. Add topics: `yt-dlp`, `youtube-downloader`, `python`, `windows`, `mp3`, `mp4`, `mkv`

## Step 8: Optional Enhancements

### Add a Logo
1. Create a logo image (PNG, 256x256 recommended)
2. Add to repository as `logo.png`
3. Update README to reference it

### Set Up Releases
1. Go to Releases
2. Click "Create a new release"
3. Tag version: `v1.0.0`
4. Release title: `v1.0.0 - Initial Release`
5. Describe the features (copy from CHANGELOG.md)

### Enable GitHub Pages (for documentation)
1. Go to Settings → Pages
2. Source: Deploy from branch
3. Branch: `main`
4. Folder: `docs/`

## Example Commands Summary

Here's the complete sequence you'll likely need:

```bash
# Configure Git (if not done before)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Commit your changes
git commit -m "Initial commit: Complete yt-dlp wrapper with tests and documentation"

# Connect to GitHub (replace with your details)
git remote add origin https://github.com/yourusername/yt-dlp-wrapper.git
git branch -M main
git push -u origin main
```

## Troubleshooting

### Authentication Issues
If you get authentication errors:
1. Use a Personal Access Token instead of password
2. Or set up SSH keys
3. GitHub has guides for both methods

### Large File Issues
If any files are too large:
1. Check `.gitignore` is working
2. Remove any accidentally tracked large files
3. Use `git rm --cached filename` to untrack files

### Test Failures
If GitHub Actions fail:
1. Check the Actions tab for details
2. Most likely cause: missing dependencies
3. The workflow should install everything automatically

## Next Steps

After deployment:
1. Share your repository with others
2. Consider adding more features
3. Respond to issues and pull requests
4. Keep dependencies updated
5. Add more comprehensive tests

Your project is now ready for the world! 🎉

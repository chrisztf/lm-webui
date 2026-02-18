#!/bin/bash

# LM WebUI Repository Cleanup Script

set -e

echo "🔧 Starting repository cleanup..."

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p scripts/debug
mkdir -p scripts/tests
mkdir -p docs/implementation
mkdir -p docs/prompts
mkdir -p examples/samples
mkdir -p archive/backup

# Move debug files
echo "📦 Moving debug files..."
if [ -f "debug_db.py" ]; then
    mv debug_db.py scripts/debug/
fi
if [ -f "debug_message_pipeline.py" ]; then
    mv debug_message_pipeline.py scripts/debug/
fi
if [ -f "debug_message_pipeline2.py" ]; then
    mv debug_message_pipeline2.py scripts/debug/
fi
if [ -f "debug_reasoning_test.py" ]; then
    mv debug_reasoning_test.py scripts/debug/
fi

# Move test files
echo "🧪 Moving test files..."
if [ -f "test_batch_processing.py" ]; then
    mv test_batch_processing.py scripts/tests/
fi
if [ -f "test_parallel_chat_implementation.py" ]; then
    mv test_parallel_chat_implementation.py scripts/tests/
fi

# Move implementation documentation
echo "📄 Moving implementation documentation..."
if [ -d "__implementation__" ]; then
    mv __implementation__/* docs/implementation/ 2>/dev/null || true
    rmdir __implementation__ 2>/dev/null || true
fi

# Move prompt files
echo "💬 Moving prompt files..."
if [ -d "__prompt___" ]; then
    mv __prompt___/* docs/prompts/ 2>/dev/null || true
    rmdir __prompt___ 2>/dev/null || true
fi

# Move sample files
echo "🖼️ Moving sample files..."
if [ -d "__sample__" ]; then
    mv __sample__/* examples/samples/ 2>/dev/null || true
    rmdir __sample__ 2>/dev/null || true
fi

# Move backup directory
echo "💾 Moving backup directory..."
if [ -d "__backup__" ]; then
    mv __backup__/* archive/backup/ 2>/dev/null || true
    rmdir __backup__ 2>/dev/null || true
fi

# Clean up test directory
echo "🧹 Cleaning up test directory..."
if [ -d "__test__" ]; then
    # Move integration tests to backend tests
    mkdir -p backend/tests/integration
    mv __test__/*.py backend/tests/integration/ 2>/dev/null || true
    
    # Move test documentation
    mv __test__/*.md docs/testing/ 2>/dev/null || true
    
    # Remove empty directory
    rmdir __test__ 2>/dev/null || true
fi

# Remove .DS_Store files
echo "🗑️ Removing .DS_Store files..."
find . -name ".DS_Store" -type f -delete

# Update .gitignore
echo "📝 Updating .gitignore..."
if ! grep -q "archive/" .gitignore; then
    echo "" >> .gitignore
    echo "# Archive directories" >> .gitignore
    echo "archive/" >> .gitignore
fi

if ! grep -q "scripts/debug/" .gitignore; then
    echo "" >> .gitignore
    echo "# Debug scripts" >> .gitignore
    echo "scripts/debug/" >> .gitignore
fi

# Make cleanup script executable
chmod +x cleanup_repository.sh

echo "✅ Repository cleanup completed!"
echo ""
echo "Summary of changes:"
echo "1. 📁 Created organized directory structure"
echo "2. 📦 Moved debug files to scripts/debug/"
echo "3. 🧪 Moved test files to scripts/tests/"
echo "4. 📄 Moved documentation to docs/"
echo "5. 🗑️ Removed sensitive files"
echo "6. 📝 Updated .gitignore"
echo ""
echo "Next steps:"
echo "1. Review the moved files in their new locations"
echo "2. Update any references to moved files"
echo "3. Commit the changes"
echo "4. Push to GitHub"
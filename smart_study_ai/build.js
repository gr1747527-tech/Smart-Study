const fs = require('fs');
const path = require('path');

// Create dist directory
const distDir = './dist';
if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

// Copy static files
const staticSource = './static';
const staticDest = './dist/static';
copyDir(staticSource, staticDest);

// Copy templates to dist
const templatesSource = './templates';
const templatesDest = './dist/templates';
copyDir(templatesSource, templatesDest);

function copyDir(src, dest) {
  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }

  const files = fs.readdirSync(src);

  files.forEach(file => {
    const srcPath = path.join(src, file);
    const destPath = path.join(dest, file);
    const stat = fs.statSync(srcPath);

    if (stat.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  });
}

console.log('✅ Build complete! dist folder created.');

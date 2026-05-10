const { CoverageReport } = require('monocart-coverage-reports');
const fs = require('fs');
const path = require('path');

const v8Dir = path.join(__dirname, '..', '.qa-runs', 'v8-coverage');

async function generate() {
    const coverageReport = new CoverageReport({
        name: 'Frontend V8 Coverage',
        outputDir: './.qa-runs/coverage-reports',
        reports: ['v8', 'cobertura'],
        entryFilter: (entry) => entry.url.startsWith('public/js/'),
        sourcePath: (fileUrl) => fileUrl // Already rewritten to local path
    });

    let hasData = false;
    if (fs.existsSync(v8Dir)) {
        for (const file of fs.readdirSync(v8Dir)) {
            if (file.endsWith('.json')) {
                const data = JSON.parse(fs.readFileSync(path.join(v8Dir, file), 'utf8'));
                if (Array.isArray(data) && data.length > 0) {
                    for (const entry of data) {
                        if (entry.url && entry.url.includes('localhost:') && entry.url.includes('/js/')) {
                            const withoutQuery = entry.url.split('?')[0];
                            const relativePath = withoutQuery.replace(/.*\/js\//, 'public/js/');
                            const localPath = path.resolve(__dirname, '..', relativePath);
                            if (fs.existsSync(localPath)) {
                                entry.source = fs.readFileSync(localPath, 'utf8');
                            }
                            entry.url = relativePath; // Rewrite URL to match git path for Cobertura
                        }
                    }
                    await coverageReport.add(data);
                    hasData = true;
                }
            }
        }
    }

    if (hasData) {
        await coverageReport.generate();
        console.log("Frontend coverage report generated at .qa-runs/coverage-reports");
    } else {
        console.log("No V8 coverage data found in .qa-runs/v8-coverage");
    }
}

generate().catch(err => {
    console.error(err);
    process.exit(1);
});
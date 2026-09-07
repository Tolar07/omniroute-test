export const meta = {
  name: 'fixtures-loop-nonstop',
  description: 'Run fixtures agent continuously with verification loop',
  phases: [
    { title: 'Run Fixtures', detail: 'Execute fixtures agent in infinite loop' },
    { title: 'Verify Results', detail: 'Verify fixture results continuously' }
  ]
}

async function run() {
  // Import required modules
  const { agent, pipeline, parallel } = require('@claude/workflow');
  const { log } = require('@claude/workflow/log');

  // Define the main loop
  while (true) {
    try {
      // Run fixtures agent
      log('Running fixtures agent...');
      const fixturesResult = await agent('python fixtures_agent.py', {
        phase: 'Run Fixtures',
        model: 'claude-sonnet-5',
        effort: 'medium'
      });

      // Parse the output to extract fixtures
      const fixtures = parseFixturesOutput(fixturesResult);

      // Run verification agent on the fixtures
      log('Verifying fixtures...');
      const verificationResult = await agent(`verify_fixtures(${fixtures})`, {
        phase: 'Verify Results',
        model: 'claude-sonnet-5',
        effort: 'high'
      });

      log(`Found ${fixtures.length} fixtures, ${verificationResult.verifiedCount} verified`);

      // Sleep for a short interval before next iteration
      await new Promise(resolve => setTimeout(resolve, 300000)); // 5 minutes
    } catch (error) {
      log(`Error: ${error.message}`);
      await new Promise(resolve => setTimeout(resolve, 60000)); // 1 minute before retry
    }
  }
}

// Helper function to parse the fixtures output
function parseFixturesOutput(output) {
  // This is a simplified parser - in reality would need more robust parsing
  const lines = output.split('\n');
  const fixtures = [];

  // Find the start of fixture data (after the header)
  const startIndex = lines.indexOf('='.repeat(80));
  if (startIndex !== -1) {
    for (let i = startIndex + 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line && !line.startsWith('=') && !line.startsWith('Total')) {
        // Parse fixture line
        const match = line.match(/(\d+) fixtures across (\d+) deploy-eligible competitions$/);
        if (match) {
          // This is the total count line, skip it
          continue;
        }

        // Parse individual fixture lines
        if (line.includes('vs')) {
          const parts = line.split(' vs ');
          if (parts.length === 2) {
            fixtures.push({
              home: parts[0].trim(),
              away: parts[1].trim(),
              verified: true // Simplified - in reality would check verification status
            });
          }
        }
      }
    }
  }

  return fixtures;
}

// Start the loop
run();
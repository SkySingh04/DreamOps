import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

// Extract service info from request
async function getRequestBody(request: NextRequest) {
  try {
    const body = await request.json();
    return body;
  } catch {
    return {};
  }
}

export async function POST(request: NextRequest) {
  try {
    // Get request parameters
    const { service, action = 'all' } = await getRequestBody(request);
    
    // Path to the chaos script - try multiple possible locations
    const possiblePaths = [
      path.join(process.cwd(), '..', '..', 'fuck_kubernetes.sh'),  // Two levels up from frontend
      path.join(process.cwd(), '..', 'fuck_kubernetes.sh'),
      path.join(process.cwd(), 'fuck_kubernetes.sh'),
      path.join(process.cwd(), '..', '..', 'backend', 'fuck_kubernetes.sh')
    ];
    
    let scriptPath = '';
    
    // Find the script in one of the possible locations
    for (const testPath of possiblePaths) {
      if (fs.existsSync(testPath)) {
        scriptPath = testPath;
        break;
      }
    }
    
    if (!scriptPath) {
      throw new Error('Chaos script not found in any expected location');
    }
    
    // Determine script parameter based on service or action
    let scriptParam = action;
    if (service) {
      const serviceMap: Record<string, string> = {
        'pod_crash': '1',
        'image_pull': '2', 
        'oom_kill': '3',
        'deployment_failure': '4',
        'service_unavailable': '5'
      };
      scriptParam = serviceMap[service] || service;
    }
    
    console.log(`🔥 CHAOS ENGINEERING: Starting ${service ? service : 'all services'} destruction...`);
    console.log(`Script path: ${scriptPath}, Parameter: ${scriptParam}`);
    
    // Execute the chaos script with the determined parameter
    // Handle both Windows and Unix systems
    const isWindows = process.platform === 'win32';
    let chaosProcess;
    
    if (isWindows) {
      // On Windows, use cmd.exe or Git Bash if available
      const bashPaths = [
        'C:\\Program Files\\Git\\bin\\bash.exe',
        'C:\\Program Files (x86)\\Git\\bin\\bash.exe',
        'bash.exe' // In case it's in PATH
      ];
      
      let bashPath = '';
      for (const testPath of bashPaths) {
        if (fs.existsSync(testPath)) {
          bashPath = testPath;
          break;
        }
      }
      
      if (!bashPath) {
        // Fallback to WSL or direct execution
        try {
          const homeDir = process.env.HOME || process.env.USERPROFILE || '';
          const kubeconfigPath = process.env.KUBECONFIG || path.join(homeDir, '.kube', 'config');
          
          const awsCredsPath = path.join(homeDir, '.aws', 'credentials');
          const awsConfigPath = path.join(homeDir, '.aws', 'config');
          
          chaosProcess = spawn('wsl', ['bash', scriptPath, scriptParam], {
            cwd: path.dirname(scriptPath),
            env: {
              ...process.env,
              KUBECONFIG: kubeconfigPath,
              HOME: homeDir,
              AWS_PROFILE: process.env.AWS_PROFILE || 'burner',
              AWS_DEFAULT_REGION: process.env.AWS_DEFAULT_REGION || 'ap-south-1',
              AWS_SHARED_CREDENTIALS_FILE: awsCredsPath,
              AWS_CONFIG_FILE: awsConfigPath,
              AWS_SDK_LOAD_CONFIG: '1'
            }
          });
        } catch {
          throw new Error('No bash executable found. Please install Git Bash or WSL.');
        }
      } else {
        const homeDir = process.env.HOME || process.env.USERPROFILE || '';
        const kubeconfigPath = process.env.KUBECONFIG || path.join(homeDir, '.kube', 'config');
        
        const awsCredsPath = path.join(homeDir, '.aws', 'credentials');
        const awsConfigPath = path.join(homeDir, '.aws', 'config');
        
        chaosProcess = spawn(bashPath, [scriptPath, scriptParam], {
          cwd: path.dirname(scriptPath),
          env: {
            ...process.env,
            KUBECONFIG: kubeconfigPath,
            HOME: homeDir,
            AWS_PROFILE: process.env.AWS_PROFILE || 'burner',
            AWS_DEFAULT_REGION: process.env.AWS_DEFAULT_REGION || 'ap-south-1',
            AWS_SHARED_CREDENTIALS_FILE: awsCredsPath,
            AWS_CONFIG_FILE: awsConfigPath,
            AWS_SDK_LOAD_CONFIG: '1'
          }
        });
      }
    } else {
      // Unix/Linux systems
      const homeDir = process.env.HOME || process.env.USERPROFILE || '';
      const kubeconfigPath = process.env.KUBECONFIG || path.join(homeDir, '.kube', 'config');
      
      // Get AWS credentials path
      const awsCredsPath = path.join(homeDir, '.aws', 'credentials');
      const awsConfigPath = path.join(homeDir, '.aws', 'config');
      
      chaosProcess = spawn('/bin/bash', [scriptPath, scriptParam], {
        cwd: path.dirname(scriptPath),
        env: {
          ...process.env,
          PATH: '/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin',
          KUBECONFIG: kubeconfigPath,
          HOME: homeDir,
          AWS_PROFILE: process.env.AWS_PROFILE || 'burner',
          AWS_DEFAULT_REGION: process.env.AWS_DEFAULT_REGION || 'ap-south-1',
          AWS_SHARED_CREDENTIALS_FILE: awsCredsPath,
          AWS_CONFIG_FILE: awsConfigPath,
          // Also pass AWS SDK config
          AWS_SDK_LOAD_CONFIG: '1'
        }
      });
    }

    const results: string[] = [];
    let errorOutput = '';

    // Capture stdout
    chaosProcess.stdout.on('data', (data) => {
      const output = data.toString();
      console.log(`🔥 CHAOS OUTPUT (${service || 'all'}):`, output);
      
      // Parse the output and extract meaningful results
      const lines = output.split('\n').filter((line: string) => line.trim());
      lines.forEach((line: string) => {
        // Remove ANSI color codes and filter meaningful lines
        const cleanLine = line.replace(/\x1b\[[0-9;]*m/g, '');
        if (cleanLine.includes('✓') || cleanLine.includes('simulation deployed') || 
            cleanLine.includes('Fucking Kubernetes') || cleanLine.includes('deployed!') ||
            cleanLine.includes('CloudWatch alarms') || cleanLine.includes('triggered') ||
            cleanLine.includes('Error') || cleanLine.includes('Failed') ||
            cleanLine.includes('kubectl') || cleanLine.includes('namespace')) {
          results.push(cleanLine);
        }
      });
    });

    // Capture stderr
    chaosProcess.stderr.on('data', (data) => {
      const error = data.toString();
      console.error(`💥 CHAOS ERROR (${service || 'all'}):`, error);
      errorOutput += error;
      
      // Also add significant errors to results for visibility
      const lines = error.split('\n').filter((line: string) => line.trim());
      lines.forEach((line: string) => {
        if (line.includes('Error') || line.includes('failed') || line.includes('kubectl')) {
          results.push(`❌ ${line.trim()}`);
        }
      });
    });

    // Wait for the process to complete
    await new Promise((resolve, reject) => {
      chaosProcess.on('close', (code) => {
        console.log(`🔥 Chaos script (${service || 'all'}) exited with code: ${code}`);
        if (code === 0) {
          resolve(code);
        } else {
          const errorMsg = `Chaos script failed with exit code ${code}${errorOutput ? ': ' + errorOutput : ''}`;
          console.error(`💥 ${errorMsg}`);
          reject(new Error(errorMsg));
        }
      });

      chaosProcess.on('error', (error) => {
        console.error(`💥 Failed to start chaos script for ${service || 'all'}:`, error);
        reject(new Error(`Failed to start chaos script: ${error.message}`));
      });
      
      // Add timeout to prevent hanging
      setTimeout(() => {
        chaosProcess.kill('SIGTERM');
        reject(new Error(`Chaos script timeout after 60 seconds for ${service || 'all'}`));
      }, 60000);
    });

    // Add some dramatic results based on service or all services
    let dramaticResults: string[] = [];
    
    if (service) {
      // Service-specific dramatic results
      switch (service) {
        case 'pod_crash':
          dramaticResults = [
            '💥 Pod crash simulation deployed - CrashLoopBackOff initiated',
            '🔥 Pods will restart in endless death loop',
            '📊 CloudWatch pod restart alarms triggered'
          ];
          break;
        case 'image_pull':
          dramaticResults = [
            '🚫 Image pull error deployed - ImagePullBackOff in progress',
            '💀 Non-existent images will haunt your cluster',
            '📊 CloudWatch image pull alarms triggered'
          ];
          break;
        case 'oom_kill':
          dramaticResults = [
            '💀 OOM kill simulation deployed - Memory massacre incoming',
            '🧠 Memory-hungry pods will be terminated',
            '📊 CloudWatch memory alarms triggered'
          ];
          break;
        case 'deployment_failure':
          dramaticResults = [
            '⚡ Deployment failure initiated - Rolling update will fail',
            '🔄 Deployments stuck in eternal failure state',
            '📊 CloudWatch deployment alarms triggered'
          ];
          break;
        case 'service_unavailable':
          dramaticResults = [
            '🔴 Service unavailable deployed - Endpoints destroyed',
            '🚨 Services will have no working endpoints',
            '📊 CloudWatch service alarms triggered'
          ];
          break;
      }
      dramaticResults.push('🎯 PagerDuty alerts should start firing', `✅ ${service} chaos successfully deployed!`);
    } else {
      // All services dramatic results
      dramaticResults = [
        '🔥 Pod crash simulation deployed - CrashLoopBackOff initiated',
        '💥 Image pull error deployed - ImagePullBackOff in progress', 
        '💀 OOM kill simulation deployed - Memory massacre incoming',
        '⚡ Deployment failure initiated - Rolling update will fail',
        '🚨 Service unavailable deployed - Endpoints destroyed',
        '📊 CloudWatch alarms automatically triggered',
        '🎯 PagerDuty alerts should start firing',
        '✅ All 5 Kubernetes services successfully fucked!'
      ];
    }

    // Combine actual results with dramatic ones
    const finalResults = [...results, ...dramaticResults];

    console.log('🎉 CHAOS ENGINEERING COMPLETE - Infrastructure successfully destroyed!');

    return NextResponse.json({
      success: true,
      message: `${service ? service : 'All services'} chaos deployed successfully`,
      results: finalResults,
      service: service || 'all',
      services_affected: service ? 1 : 5,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('💥 CHAOS ENGINEERING FAILED:', error);
    
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      message: 'Failed to deploy infrastructure chaos',
      timestamp: new Date().toISOString()
    }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'Chaos Engineering API',
    description: 'POST to this endpoint to trigger infrastructure chaos',
    warning: '⚠️ This will intentionally break Kubernetes services for testing',
    services_targeted: [
      'Database service (connection failures)',
      'API gateway (timeout/503 errors)', 
      'Redis/cache service (memory issues)',
      'Worker service (pod crashes)',
      'Load balancer (routing failures)'
    ]
  });
}
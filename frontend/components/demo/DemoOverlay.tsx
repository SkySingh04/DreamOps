'use client';

import React from 'react';
import { useDemo } from '@/lib/demo/DemoContext';
import { AnimatedCursor, DemoStyles } from './AnimatedCursor';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { 
  Play, 
  Pause, 
  Square, 
  Volume2,
  VolumeX,
  Settings,
  Maximize2,
  Minimize2,
  Film
} from 'lucide-react';
import { 
  DEMO_ANALYSIS_STEPS, 
  DEMO_RESOLUTION_ACTIONS, 
  DEMO_FINDINGS,
  MOCK_INCIDENT 
} from '@/lib/demo/mockData';

interface DemoOverlayProps {
  className?: string;
}

export function DemoOverlay({ className = '' }: DemoOverlayProps) {
  const { state, pauseDemo, resumeDemo, stopDemo, setSpeed, getCurrentStep, getTotalSteps } = useDemo();
  const [isMinimized, setIsMinimized] = React.useState(false);
  const [soundEnabled, setSoundEnabled] = React.useState(true);

  if (!state.isActive) return null;

  const currentStep = getCurrentStep();
  const totalSteps = getTotalSteps();

  return (
    <>
      <DemoStyles />
      <AnimatedCursor />
      
      {/* Main Demo Overlay */}
      <div className={`fixed inset-0 bg-black/20 backdrop-blur-sm z-50 pointer-events-none ${className}`}>
        <div className="absolute top-4 left-4 right-4 pointer-events-auto">
          <Card className="bg-white/95 backdrop-blur border-2 border-blue-200 shadow-xl">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <Film className="h-5 w-5 text-blue-600" />
                    <span className="font-semibold text-blue-900">Demo Mode</span>
                  </div>
                  {currentStep && (
                    <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                      Step {state.currentStep + 1} of {totalSteps}: {currentStep.title}
                    </Badge>
                  )}
                </div>
                
                <div className="flex items-center gap-2">
                  {/* Speed Control */}
                  <select 
                    value={state.speed} 
                    onChange={(e) => setSpeed(Number(e.target.value))}
                    className="text-sm border rounded px-2 py-1 bg-white"
                  >
                    <option value="0.5">0.5x</option>
                    <option value="1">1x</option>
                    <option value="1.5">1.5x</option>
                    <option value="2">2x</option>
                  </select>
                  
                  {/* Sound Toggle */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSoundEnabled(!soundEnabled)}
                  >
                    {soundEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                  </Button>
                  
                  {/* Minimize/Maximize */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsMinimized(!isMinimized)}
                  >
                    {isMinimized ? <Maximize2 className="h-4 w-4" /> : <Minimize2 className="h-4 w-4" />}
                  </Button>
                  
                  {/* Pause/Resume */}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={state.isPaused ? resumeDemo : pauseDemo}
                  >
                    {state.isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
                  </Button>
                  
                  {/* Stop */}
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={stopDemo}
                  >
                    <Square className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              {!isMinimized && (
                <div className="mt-4 space-y-3">
                  {/* Progress Bar */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Progress</span>
                      <span>{Math.round(state.progress)}%</span>
                    </div>
                    <Progress value={state.progress} className="h-2" />
                  </div>
                  
                  {/* Status Info */}
                  {state.isPaused && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded p-2 text-sm text-yellow-800">
                      ⏸️ Demo paused - Click play to continue
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Incident Alert Overlay */}
      {state.incidentTriggered && currentStep?.id === 'trigger' && (
        <div className="fixed top-20 right-4 z-60 pointer-events-none">
          <Card className="bg-red-50 border-2 border-red-200 shadow-xl animate-pulse">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="h-3 w-3 bg-red-500 rounded-full animate-ping"></div>
                <div>
                  <h3 className="font-semibold text-red-900">🚨 Critical Alert</h3>
                  <p className="text-sm text-red-700">{MOCK_INCIDENT.title}</p>
                  <p className="text-xs text-red-600 mt-1">{MOCK_INCIDENT.description}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* AI Analysis Overlay */}
      {state.isAnalyzing && (
        <div className="fixed top-20 left-1/2 transform -translate-x-1/2 z-60 pointer-events-none">
          <Card className="bg-blue-50 border-2 border-blue-200 shadow-xl min-w-96">
            <CardContent className="p-4">
              <div className="space-y-3">
                <h3 className="font-semibold text-blue-900 flex items-center gap-2">
                  <div className="h-2 w-2 bg-blue-500 rounded-full animate-pulse"></div>
                  AI Agent Analysis
                </h3>
                
                <div className="space-y-2">
                  {DEMO_ANALYSIS_STEPS.map((step, index) => (
                    <div key={index} className={`flex items-center gap-2 text-sm ${
                      index <= state.analysisStep ? 'text-blue-700' : 'text-gray-400'
                    }`}>
                      {index < state.analysisStep ? (
                        <span className="text-green-500">✓</span>
                      ) : index === state.analysisStep ? (
                        <div className="h-2 w-2 bg-blue-500 rounded-full animate-spin"></div>
                      ) : (
                        <span className="text-gray-300">○</span>
                      )}
                      {step}
                    </div>
                  ))}
                </div>
                
                {state.analysisStep >= 6 && (
                  <div className="mt-4 p-3 bg-white rounded border border-blue-200">
                    <h4 className="font-medium text-sm text-blue-900 mb-2">Findings:</h4>
                    <p className="text-sm text-blue-700">{DEMO_FINDINGS.rootCause}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* AI Resolution Overlay */}
      {state.isResolving && (
        <div className="fixed top-20 left-1/2 transform -translate-x-1/2 z-60 pointer-events-none">
          <Card className="bg-green-50 border-2 border-green-200 shadow-xl min-w-96">
            <CardContent className="p-4">
              <div className="space-y-3">
                <h3 className="font-semibold text-green-900 flex items-center gap-2">
                  <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                  Automated Resolution
                </h3>
                
                <div className="space-y-3">
                  {DEMO_RESOLUTION_ACTIONS.map((action, index) => (
                    <div key={index} className={`space-y-1 ${
                      index <= state.resolutionStep ? 'opacity-100' : 'opacity-50'
                    }`}>
                      <div className="flex items-center gap-2 text-sm">
                        {index < state.resolutionStep ? (
                          <span className="text-green-600">✅</span>
                        ) : index === state.resolutionStep ? (
                          <div className="h-2 w-2 bg-green-500 rounded-full animate-spin"></div>
                        ) : (
                          <span className="text-gray-300">○</span>
                        )}
                        <span className={index <= state.resolutionStep ? 'text-green-700' : 'text-gray-400'}>
                          {action.action}
                        </span>
                      </div>
                      <p className={`text-xs ml-4 ${
                        index <= state.resolutionStep ? 'text-green-600' : 'text-gray-400'
                      }`}>
                        {action.description}
                      </p>
                      {index === state.resolutionStep && (
                        <div className="ml-4">
                          <Progress value={75} className="h-1 w-32" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Completion Overlay */}
      {state.completedAt && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-70 pointer-events-auto">
          <Card className="bg-white shadow-2xl max-w-md mx-4">
            <CardContent className="p-6 text-center">
              <div className="mb-4">
                <div className="h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">🎉</span>
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">Demo Complete!</h2>
                <p className="text-gray-600">
                  Incident resolved in 2m 34s using AI-powered automation
                </p>
              </div>
              
              <div className="space-y-2 text-sm text-left">
                <div className="flex justify-between">
                  <span>Integrations Set Up:</span>
                  <span className="font-medium">5/5</span>
                </div>
                <div className="flex justify-between">
                  <span>Incident Response Time:</span>
                  <span className="font-medium">2m 34s</span>
                </div>
                <div className="flex justify-between">
                  <span>Actions Executed:</span>
                  <span className="font-medium">8</span>
                </div>
                <div className="flex justify-between">
                  <span>Success Rate:</span>
                  <span className="font-medium text-green-600">100%</span>
                </div>
              </div>
              
              <Button onClick={stopDemo} className="w-full mt-4">
                Close Demo
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
'use client';

import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { MOCK_INTEGRATIONS, MOCK_INCIDENT, MockIntegration } from './mockData';

export interface DemoStep {
  id: string;
  title: string;
  page?: string;
  duration: number;
  actions: DemoAction[];
}

export interface DemoAction {
  type: 'navigate' | 'click' | 'type' | 'wait' | 'highlight' | 'toast' | 'trigger_incident' | 'show_analysis' | 'show_resolution' | 'start_analysis' | 'start_resolution';
  target?: string;
  value?: string;
  delay?: number;
  message?: string;
  integration?: string;
}

export interface DemoState {
  isActive: boolean;
  currentStep: number;
  currentActionIndex: number;
  isPaused: boolean;
  speed: number;
  progress: number;
  integrations: Record<string, MockIntegration>;
  incidentTriggered: boolean;
  analysisStep: number;
  resolutionStep: number;
  isAnalyzing: boolean;
  isResolving: boolean;
  completedAt?: string;
}

type DemoActionType =
  | { type: 'START_DEMO' }
  | { type: 'STOP_DEMO' }
  | { type: 'PAUSE_DEMO' }
  | { type: 'RESUME_DEMO' }
  | { type: 'SET_SPEED'; speed: number }
  | { type: 'NEXT_STEP' }
  | { type: 'NEXT_ACTION' }
  | { type: 'SET_PROGRESS'; progress: number }
  | { type: 'ENABLE_INTEGRATION'; name: string }
  | { type: 'TRIGGER_INCIDENT' }
  | { type: 'NEXT_ANALYSIS_STEP' }
  | { type: 'NEXT_RESOLUTION_STEP' }
  | { type: 'START_ANALYSIS' }
  | { type: 'START_RESOLUTION' }
  | { type: 'COMPLETE_DEMO' };

const initialState: DemoState = {
  isActive: false,
  currentStep: 0,
  currentActionIndex: 0,
  isPaused: false,
  speed: 1,
  progress: 0,
  integrations: { ...MOCK_INTEGRATIONS },
  incidentTriggered: false,
  analysisStep: 0,
  resolutionStep: 0,
  isAnalyzing: false,
  isResolving: false,
};

const DEMO_STEPS: DemoStep[] = [
  {
    id: 'start',
    title: 'Starting Demo Mode',
    duration: 2000,
    actions: [
      { type: 'toast', message: '🎬 Demo Mode Activated', delay: 500 },
      { type: 'wait', delay: 1500 }
    ]
  },
  {
    id: 'integrations',
    title: 'Setting up Integrations',
    page: '/integrations',
    duration: 15000,
    actions: [
      { type: 'navigate', target: '/integrations' },
      { type: 'wait', delay: 1000 },
      { type: 'toast', message: 'Setting up PagerDuty integration...', delay: 500 },
      { type: 'wait', delay: 1500 },
      { type: 'toast', message: '✅ PagerDuty connected', delay: 100 },
      { type: 'wait', delay: 1000 },
      { type: 'toast', message: 'Setting up Kubernetes integration...', delay: 500 },
      { type: 'wait', delay: 1500 },
      { type: 'toast', message: '✅ Kubernetes connected', delay: 100 },
      { type: 'wait', delay: 1000 },
      { type: 'toast', message: 'Setting up GitHub integration...', delay: 500 },
      { type: 'wait', delay: 1500 },
      { type: 'toast', message: '✅ GitHub connected', delay: 100 },
      { type: 'wait', delay: 1000 },
      { type: 'toast', message: 'Setting up Notion integration...', delay: 500 },
      { type: 'wait', delay: 1500 },
      { type: 'toast', message: '✅ Notion connected', delay: 100 },
      { type: 'wait', delay: 1000 },
      { type: 'toast', message: 'Setting up Grafana integration...', delay: 500 },
      { type: 'wait', delay: 1500 },
      { type: 'toast', message: '✅ Grafana connected', delay: 100 },
      { type: 'wait', delay: 500 }
    ]
  },
  {
    id: 'trigger',
    title: 'Triggering Critical Incident',
    page: '/dashboard',
    duration: 5000,
    actions: [
      { type: 'navigate', target: '/dashboard' },
      { type: 'wait', delay: 1000 },
      { type: 'trigger_incident' },
      { type: 'toast', message: '🚨 Critical Alert: Payment Service Down', delay: 500 },
      { type: 'wait', delay: 2000 },
      { type: 'toast', message: 'AI Agent activated for incident response', delay: 500 },
      { type: 'wait', delay: 1500 }
    ]
  },
  {
    id: 'analysis',
    title: 'AI Agent Analysis',
    duration: 12000,
    actions: [
      { type: 'start_analysis' },
      { type: 'show_analysis' }
    ]
  },
  {
    id: 'resolution',
    title: 'Automated Resolution',
    duration: 10000,
    actions: [
      { type: 'start_resolution' },
      { type: 'show_resolution' }
    ]
  },
  {
    id: 'complete',
    title: 'Demo Complete',
    page: '/dashboard',
    duration: 3000,
    actions: [
      { type: 'navigate', target: '/dashboard' },
      { type: 'wait', delay: 1000 },
      { type: 'toast', message: '✨ Incident resolved in 2m 34s', delay: 500 },
      { type: 'wait', delay: 1500 },
      { type: 'toast', message: '🎉 Demo completed successfully!', delay: 500 },
      { type: 'wait', delay: 1000 }
    ]
  }
];

function demoReducer(state: DemoState, action: DemoActionType): DemoState {
  switch (action.type) {
    case 'START_DEMO':
      return {
        ...initialState,
        isActive: true,
        integrations: { ...MOCK_INTEGRATIONS }
      };
    
    case 'STOP_DEMO':
      return {
        ...initialState,
        integrations: { ...MOCK_INTEGRATIONS }
      };
    
    case 'PAUSE_DEMO':
      return { ...state, isPaused: true };
    
    case 'RESUME_DEMO':
      return { ...state, isPaused: false };
    
    case 'SET_SPEED':
      return { ...state, speed: action.speed };
    
    case 'NEXT_STEP':
      const nextStep = Math.min(state.currentStep + 1, DEMO_STEPS.length - 1);
      return {
        ...state,
        currentStep: nextStep,
        currentActionIndex: 0,
        progress: (nextStep / (DEMO_STEPS.length - 1)) * 100
      };
    
    case 'NEXT_ACTION':
      return {
        ...state,
        currentActionIndex: state.currentActionIndex + 1
      };
    
    case 'SET_PROGRESS':
      return { ...state, progress: action.progress };
    
    case 'ENABLE_INTEGRATION':
      return {
        ...state,
        integrations: {
          ...state.integrations,
          [action.name]: {
            ...state.integrations[action.name],
            enabled: true
          }
        }
      };
    
    case 'TRIGGER_INCIDENT':
      return { ...state, incidentTriggered: true };
    
    case 'START_ANALYSIS':
      return { ...state, isAnalyzing: true, analysisStep: 0 };
    
    case 'NEXT_ANALYSIS_STEP':
      return { ...state, analysisStep: state.analysisStep + 1 };
    
    case 'START_RESOLUTION':
      return { ...state, isAnalyzing: false, isResolving: true, resolutionStep: 0 };
    
    case 'NEXT_RESOLUTION_STEP':
      return { ...state, resolutionStep: state.resolutionStep + 1 };
    
    case 'COMPLETE_DEMO':
      return {
        ...state,
        isActive: false,
        isAnalyzing: false,
        isResolving: false,
        completedAt: new Date().toISOString()
      };
    
    default:
      return state;
  }
}

interface DemoContextType {
  state: DemoState;
  startDemo: () => void;
  stopDemo: () => void;
  pauseDemo: () => void;
  resumeDemo: () => void;
  setSpeed: (speed: number) => void;
  getCurrentStep: () => DemoStep | null;
  getTotalSteps: () => number;
}

const DemoContext = createContext<DemoContextType | null>(null);

export function DemoProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(demoReducer, initialState);
  const router = useRouter();

  const startDemo = useCallback(() => {
    dispatch({ type: 'START_DEMO' });
  }, []);

  const stopDemo = useCallback(() => {
    dispatch({ type: 'STOP_DEMO' });
  }, []);

  const pauseDemo = useCallback(() => {
    dispatch({ type: 'PAUSE_DEMO' });
  }, []);

  const resumeDemo = useCallback(() => {
    dispatch({ type: 'RESUME_DEMO' });
  }, []);

  const setSpeed = useCallback((speed: number) => {
    dispatch({ type: 'SET_SPEED', speed });
  }, []);

  const getCurrentStep = useCallback(() => {
    return DEMO_STEPS[state.currentStep] || null;
  }, [state.currentStep]);

  const getTotalSteps = useCallback(() => {
    return DEMO_STEPS.length;
  }, []);

  // Demo execution logic
  useEffect(() => {
    if (!state.isActive || state.isPaused) return;

    const currentStep = DEMO_STEPS[state.currentStep];
    if (!currentStep) return;

    const currentAction = currentStep.actions[state.currentActionIndex];
    if (!currentAction) {
      // Move to next step
      if (state.currentStep < DEMO_STEPS.length - 1) {
        setTimeout(() => {
          dispatch({ type: 'NEXT_STEP' });
        }, 500 / state.speed);
      } else {
        // Demo complete
        dispatch({ type: 'COMPLETE_DEMO' });
      }
      return;
    }

    const executeAction = async () => {
      const delay = (currentAction.delay || 500) / state.speed;
      
      switch (currentAction.type) {
        case 'navigate':
          if (currentAction.target) {
            try {
              router.push(currentAction.target);
            } catch (error) {
              console.error('Demo navigation failed:', error);
              toast.error('Navigation failed during demo');
            }
          }
          break;
        
        case 'toast':
          if (currentAction.message) {
            toast.info(currentAction.message);
          }
          // Enable integration if specified
          if (currentAction.integration) {
            dispatch({ type: 'ENABLE_INTEGRATION', name: currentAction.integration });
          }
          break;
        
        case 'trigger_incident':
          dispatch({ type: 'TRIGGER_INCIDENT' });
          break;
        
        case 'start_analysis':
          dispatch({ type: 'START_ANALYSIS' });
          break;
        
        case 'start_resolution':
          dispatch({ type: 'START_RESOLUTION' });
          break;
        
        case 'wait':
          // Just wait for the delay
          break;
      }

      setTimeout(() => {
        dispatch({ type: 'NEXT_ACTION' });
      }, delay);
    };

    executeAction();
  }, [state.isActive, state.isPaused, state.currentStep, state.currentActionIndex, state.speed, router]);

  // Analysis step progression
  useEffect(() => {
    if (!state.isAnalyzing) return;

    const timer = setTimeout(() => {
      if (state.analysisStep < 6) {
        dispatch({ type: 'NEXT_ANALYSIS_STEP' });
      } else {
        dispatch({ type: 'START_RESOLUTION' });
      }
    }, 1500 / state.speed);

    return () => clearTimeout(timer);
  }, [state.isAnalyzing, state.analysisStep, state.speed]);

  // Resolution step progression
  useEffect(() => {
    if (!state.isResolving) return;

    const timer = setTimeout(() => {
      if (state.resolutionStep < 4) {
        dispatch({ type: 'NEXT_RESOLUTION_STEP' });
      } else {
        dispatch({ type: 'NEXT_STEP' }); // Move to completion step
      }
    }, 2000 / state.speed);

    return () => clearTimeout(timer);
  }, [state.isResolving, state.resolutionStep, state.speed]);

  return (
    <DemoContext.Provider value={{
      state,
      startDemo,
      stopDemo,
      pauseDemo,
      resumeDemo,
      setSpeed,
      getCurrentStep,
      getTotalSteps
    }}>
      {children}
    </DemoContext.Provider>
  );
}

export function useDemo() {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error('useDemo must be used within a DemoProvider');
  }
  return context;
}
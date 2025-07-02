import { Button } from '@/components/ui/button';
import { ArrowRight, AlertCircle, Bot, Clock, Shield, Search, Zap, Lock, GitBranch, Activity, Database, MessageSquare, Bell } from 'lucide-react';
import { Terminal } from './terminal';
import Link from 'next/link';

export default function HomePage() {
  return (
    <main>
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-12 lg:gap-8">
            <div className="sm:text-center md:max-w-2xl md:mx-auto lg:col-span-6 lg:text-left">
              <h1 className="text-4xl font-bold text-gray-900 tracking-tight sm:text-5xl md:text-6xl">
                AI-Powered
                <span className="block text-orange-500">On-Call Automation</span>
              </h1>
              <p className="mt-3 text-base text-gray-500 sm:mt-5 sm:text-xl lg:text-lg xl:text-xl">
                Let AI handle your 3am incidents while you sleep. Our intelligent agent automatically 
                triages, debugs, and resolves incidents using your existing DevOps stack.
              </p>
              <div className="mt-8 sm:max-w-lg sm:mx-auto sm:text-center lg:text-left lg:mx-0 flex flex-col sm:flex-row gap-4">
                <Link href="/sign-up">
                  <Button
                    size="lg"
                    className="text-lg rounded-full"
                  >
                    Start Free Trial
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
                <Link href="#how-it-works">
                  <Button
                    size="lg"
                    variant="outline"
                    className="text-lg rounded-full"
                  >
                    View Demo
                  </Button>
                </Link>
              </div>
            </div>
            <div className="mt-12 relative sm:max-w-lg sm:mx-auto lg:mt-0 lg:max-w-none lg:mx-0 lg:col-span-6 lg:flex lg:items-center">
              <Terminal />
            </div>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="py-16 bg-gray-50 w-full">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900">How It Works</h2>
            <p className="mt-4 max-w-2xl mx-auto text-xl text-gray-500">
              From alert to resolution in minutes, not hours
            </p>
          </div>
          <div className="mt-12">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-4">
              <div className="relative text-center">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-orange-500 text-white mx-auto">
                  <AlertCircle className="h-6 w-6" />
                </div>
                <div className="mt-4">
                  <h3 className="text-lg font-medium text-gray-900">1. Alert Fires</h3>
                  <p className="mt-2 text-base text-gray-500">
                    Your server goes down or service fails. PagerDuty alert triggers automatically.
                  </p>
                </div>
              </div>
              <div className="relative text-center">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-orange-500 text-white mx-auto">
                  <Bot className="h-6 w-6" />
                </div>
                <div className="mt-4">
                  <h3 className="text-lg font-medium text-gray-900">2. AI Agent Activates</h3>
                  <p className="mt-2 text-base text-gray-500">
                    Our AI agent receives the alert and starts gathering context immediately.
                  </p>
                </div>
              </div>
              <div className="relative text-center">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-orange-500 text-white mx-auto">
                  <Search className="h-6 w-6" />
                </div>
                <div className="mt-4">
                  <h3 className="text-lg font-medium text-gray-900">3. Debug & Analyze</h3>
                  <p className="mt-2 text-base text-gray-500">
                    Agent pulls data from K8s, Grafana, logs, and documentation to identify root cause.
                  </p>
                </div>
              </div>
              <div className="relative text-center">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-orange-500 text-white mx-auto">
                  <Zap className="h-6 w-6" />
                </div>
                <div className="mt-4">
                  <h3 className="text-lg font-medium text-gray-900">4. Auto-Resolve</h3>
                  <p className="mt-2 text-base text-gray-500">
                    Agent executes safe fixes or provides exact steps for resolution.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-16 bg-white w-full">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">Key Features</h2>
            <p className="mt-4 max-w-2xl mx-auto text-xl text-gray-500">
              Everything you need to automate incident response
            </p>
          </div>
          <div className="lg:grid lg:grid-cols-3 lg:gap-8">
            <div className="text-center">
              <div className="flex items-center justify-center h-12 w-12 rounded-md bg-orange-500 text-white mx-auto">
                <Clock className="h-6 w-6" />
              </div>
              <div className="mt-5">
                <h2 className="text-lg font-medium text-gray-900">
                  Reduce MTTR by 80%
                </h2>
                <p className="mt-2 text-base text-gray-500">
                  Automated debugging and resolution means incidents are fixed in minutes, not hours.
                </p>
              </div>
            </div>

            <div className="mt-10 lg:mt-0 text-center">
              <div className="flex items-center justify-center h-12 w-12 rounded-md bg-orange-500 text-white mx-auto">
                <Activity className="h-6 w-6" />
              </div>
              <div className="mt-5">
                <h2 className="text-lg font-medium text-gray-900">
                  Smart Operation Modes
                </h2>
                <p className="mt-2 text-base text-gray-500">
                  YOLO mode for auto-execution, Plan mode for review, and Approval mode for critical actions.
                </p>
              </div>
            </div>

            <div className="mt-10 lg:mt-0 text-center">
              <div className="flex items-center justify-center h-12 w-12 rounded-md bg-orange-500 text-white mx-auto">
                <Lock className="h-6 w-6" />
              </div>
              <div className="mt-5">
                <h2 className="text-lg font-medium text-gray-900">
                  Risk-Based Automation
                </h2>
                <p className="mt-2 text-base text-gray-500">
                  AI evaluates risk before actions. Only executes high-confidence, low-risk operations automatically.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-16 bg-gray-50 w-full">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">Integrations</h2>
            <p className="mt-4 max-w-2xl mx-auto text-xl text-gray-500">
              Works seamlessly with your existing DevOps stack
            </p>
          </div>
          <div className="grid grid-cols-2 gap-8 md:grid-cols-3 lg:grid-cols-4">
            <div className="col-span-1 flex justify-center items-center">
              <div className="text-center">
                <div className="h-16 w-16 mx-auto bg-[#06AC38] rounded-lg flex items-center justify-center">
                  <Bell className="h-8 w-8 text-white" />
                </div>
                <p className="mt-2 text-sm font-medium text-gray-900">PagerDuty</p>
              </div>
            </div>
            <div className="col-span-1 flex justify-center items-center">
              <div className="text-center">
                <div className="h-16 w-16 mx-auto bg-[#326CE5] rounded-lg flex items-center justify-center">
                  <svg className="h-8 w-8 text-white" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M10.204 14.35c.163 0 .326-.063.451-.189l3.695-3.695c.25-.25.25-.654 0-.904l-3.695-3.695c-.25-.25-.654-.25-.904 0-.25.25-.25.654 0 .904l3.243 3.243-3.243 3.243c-.25.25-.25.654 0 .904.125.126.288.189.453.189z"/>
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
                  </svg>
                </div>
                <p className="mt-2 text-sm font-medium text-gray-900">Kubernetes</p>
              </div>
            </div>
            <div className="col-span-1 flex justify-center items-center">
              <div className="text-center">
                <div className="h-16 w-16 mx-auto bg-[#F46800] rounded-lg flex items-center justify-center">
                  <Activity className="h-8 w-8 text-white" />
                </div>
                <p className="mt-2 text-sm font-medium text-gray-900">Grafana</p>
              </div>
            </div>
            <div className="col-span-1 flex justify-center items-center">
              <div className="text-center">
                <div className="h-16 w-16 mx-auto bg-[#4A154B] rounded-lg flex items-center justify-center">
                  <MessageSquare className="h-8 w-8 text-white" />
                </div>
                <p className="mt-2 text-sm font-medium text-gray-900">Slack</p>
              </div>
            </div>
            <div className="col-span-1 flex justify-center items-center">
              <div className="text-center">
                <div className="h-16 w-16 mx-auto bg-[#24292E] rounded-lg flex items-center justify-center">
                  <GitBranch className="h-8 w-8 text-white" />
                </div>
                <p className="mt-2 text-sm font-medium text-gray-900">GitHub</p>
              </div>
            </div>
            <div className="col-span-1 flex justify-center items-center">
              <div className="text-center">
                <div className="h-16 w-16 mx-auto bg-[#000000] rounded-lg flex items-center justify-center">
                  <Database className="h-8 w-8 text-white" />
                </div>
                <p className="mt-2 text-sm font-medium text-gray-900">Notion</p>
              </div>
            </div>
            <div className="col-span-1 flex justify-center items-center">
              <div className="text-center">
                <div className="h-16 w-16 mx-auto bg-[#632CA6] rounded-lg flex items-center justify-center">
                  <Activity className="h-8 w-8 text-white" />
                </div>
                <p className="mt-2 text-sm font-medium text-gray-900">Datadog</p>
              </div>
            </div>
            <div className="col-span-1 flex justify-center items-center">
              <div className="text-center">
                <div className="h-16 w-16 mx-auto bg-[#FF9900] rounded-lg flex items-center justify-center">
                  <svg className="h-8 w-8 text-white" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M10.344 17.757l-4.758-4.758 1.414-1.414 3.344 3.344 7.071-7.071 1.414 1.414z"/>
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
                  </svg>
                </div>
                <p className="mt-2 text-sm font-medium text-gray-900">CloudWatch</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-16 bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-2 lg:gap-8 lg:items-center">
            <div>
              <h2 className="text-3xl font-bold text-white sm:text-4xl">
                Stop getting paged at 3am
              </h2>
              <p className="mt-3 max-w-3xl text-lg text-gray-300">
                Join engineering teams that have reduced their on-call burden by 80%. 
                Let AI handle the routine incidents while you focus on building great products.
              </p>
              <div className="mt-8 flex items-center gap-6">
                <div>
                  <p className="text-4xl font-bold text-orange-500">80%</p>
                  <p className="text-sm text-gray-400">Faster MTTR</p>
                </div>
                <div>
                  <p className="text-4xl font-bold text-orange-500">24/7</p>
                  <p className="text-sm text-gray-400">Coverage</p>
                </div>
                <div>
                  <p className="text-4xl font-bold text-orange-500">5min</p>
                  <p className="text-sm text-gray-400">Setup time</p>
                </div>
              </div>
            </div>
            <div className="mt-8 lg:mt-0 flex justify-center lg:justify-end">
              <div className="max-w-sm w-full bg-white rounded-lg shadow-xl p-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Start your free trial</h3>
                <p className="text-gray-600 mb-6">No credit card required. 14-day free trial.</p>
                <Link href="/sign-up" className="block w-full">
                  <Button
                    size="lg"
                    className="w-full text-lg"
                  >
                    Get Started
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
                <p className="mt-4 text-sm text-center text-gray-500">
                  Questions? <Link href="mailto:support@oncall-ai.com" className="text-orange-500 hover:underline">Contact us</Link>
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

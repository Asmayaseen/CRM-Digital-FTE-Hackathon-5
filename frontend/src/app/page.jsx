import Link from 'next/link';
import LiveStats from '@/components/LiveStats';

const FEATURES = [
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    color: 'from-blue-500 to-blue-600',
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    title: 'Instant AI Responses',
    desc: 'LLaMA 4-powered agent resolves tickets in seconds — no waiting, no queues, no frustration.',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    color: 'from-violet-500 to-violet-600',
    bg: 'bg-violet-50 dark:bg-violet-900/20',
    title: '24 / 7 Availability',
    desc: 'Your AI support agent never sleeps. Get help at 3 AM on a Sunday — same quality, every time.',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
    color: 'from-emerald-500 to-emerald-600',
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    title: 'Multi-Channel Support',
    desc: 'Reach us via Gmail, WhatsApp, or the web form. One AI agent, three channels — your choice.',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    color: 'from-orange-500 to-orange-600',
    bg: 'bg-orange-50 dark:bg-orange-900/20',
    title: 'Smart Knowledge Base',
    desc: 'pgvector-powered semantic search finds the right answer from thousands of docs instantly.',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
    ),
    color: 'from-pink-500 to-pink-600',
    bg: 'bg-pink-50 dark:bg-pink-900/20',
    title: 'Full Ticket Tracking',
    desc: 'Every conversation logged and tracked. Check status, read replies, and see resolution notes anytime.',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
    color: 'from-cyan-500 to-cyan-600',
    bg: 'bg-cyan-50 dark:bg-cyan-900/20',
    title: 'Auto Escalation',
    desc: 'Complex issues? The agent automatically escalates billing, legal, and refund cases to human agents.',
  },
];

const STEPS = [
  {
    num: '01',
    title: 'Submit Your Request',
    desc: 'Fill out the web form, send a WhatsApp message, or email us — whatever is easiest for you.',
    color: 'text-blue-600 dark:text-blue-400',
    border: 'border-blue-200 dark:border-blue-800',
    bg: 'bg-blue-50 dark:bg-blue-900/20',
  },
  {
    num: '02',
    title: 'AI Agent Analyzes',
    desc: 'Our LLaMA 4 agent reads your issue, checks your account history, and searches the knowledge base.',
    color: 'text-violet-600 dark:text-violet-400',
    border: 'border-violet-200 dark:border-violet-800',
    bg: 'bg-violet-50 dark:bg-violet-900/20',
  },
  {
    num: '03',
    title: 'Get a Resolution',
    desc: 'Receive a detailed, personalized response in seconds. Check your ticket status anytime.',
    color: 'text-emerald-600 dark:text-emerald-400',
    border: 'border-emerald-200 dark:border-emerald-800',
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
  },
];

const CHANNELS = [
  {
    icon: (
      <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347zM12 0C5.373 0 0 5.373 0 12c0 2.125.557 4.118 1.528 5.852L.057 23.428a.5.5 0 00.515.572l5.687-1.491A11.945 11.945 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-1.986 0-3.853-.574-5.437-1.567l-.389-.232-4.035 1.057 1.077-3.929-.254-.404A9.945 9.945 0 012 12C2 6.486 6.486 2 12 2s10 4.486 10 10-4.486 10-10 10z"/>
      </svg>
    ),
    color: 'text-green-500',
    bg: 'bg-green-50 dark:bg-green-900/20',
    border: 'border-green-100 dark:border-green-800/40',
    title: 'WhatsApp',
    desc: 'Message us on WhatsApp and get an instant AI response — no app switching required.',
    tag: 'Most popular',
    tagColor: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400',
  },
  {
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
    color: 'text-blue-500',
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-100 dark:border-blue-800/40',
    title: 'Gmail / Email',
    desc: 'Send an email to our support address. The AI reads and responds directly to your inbox.',
    tag: 'Async friendly',
    tagColor: 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400',
  },
  {
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    color: 'text-violet-500',
    bg: 'bg-violet-50 dark:bg-violet-900/20',
    border: 'border-violet-100 dark:border-violet-800/40',
    title: 'Web Form',
    desc: 'Submit a structured ticket with category and priority. Track your conversation right here.',
    tag: 'Best for tracking',
    tagColor: 'bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-400',
  },
];


export default function LandingPage() {
  return (
    <div className="overflow-x-hidden">

      {/* ── HERO ── */}
      <section className="relative pt-20 pb-28 px-4 sm:px-6 text-center overflow-hidden">
        {/* Background blobs */}
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-gradient-to-br from-blue-100 to-violet-100 dark:from-blue-950 dark:to-violet-950 rounded-full blur-3xl opacity-60" />
          <div className="absolute -top-20 -right-20 w-96 h-96 bg-blue-200 dark:bg-blue-900 rounded-full blur-3xl opacity-30" />
          <div className="absolute top-40 -left-20 w-80 h-80 bg-violet-200 dark:bg-violet-900 rounded-full blur-3xl opacity-30" />
        </div>

        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-50 dark:bg-blue-900/40 border border-blue-200 dark:border-blue-700 rounded-full text-sm text-blue-700 dark:text-blue-300 font-medium mb-6 animate-fade-in">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse-slow"></span>
          AI Agent is live and responding
        </div>

        {/* Headline */}
        <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-gray-900 dark:text-white leading-tight mb-6 animate-fade-up">
          Support that never
          <br />
          <span className="gradient-text">sleeps.</span>
        </h1>

        <p className="text-xl text-gray-500 dark:text-gray-400 max-w-2xl mx-auto mb-10 animate-fade-up">
          CloudSync Pro&apos;s AI-powered Digital FTE resolves customer issues in seconds —
          across WhatsApp, Gmail, and Web, all day, every day.
        </p>

        {/* CTAs */}
        <div className="flex flex-wrap items-center justify-center gap-4 mb-16 animate-fade-up">
          <Link href="/support" className="btn-primary text-base py-3 px-8 shadow-xl shadow-blue-200 dark:shadow-blue-900">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            Get Support Now
          </Link>
          <Link href="/support#status" className="btn-secondary text-base py-3 px-8">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            Check Ticket Status
          </Link>
        </div>

        {/* Stats — live from API */}
        <LiveStats />
      </section>

      {/* ── FEATURES ── */}
      <section id="features" className="py-24 px-4 sm:px-6 bg-white dark:bg-slate-900">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-widest mb-3">Features</p>
            <h2 className="section-heading mb-4">Everything you need,<br />nothing you don&apos;t</h2>
            <p className="section-sub">Built for speed, reliability, and customer delight.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map(f => (
              <div key={f.title}
                className="group p-6 rounded-2xl border border-gray-100 dark:border-slate-700
                           hover:border-blue-200 dark:hover:border-blue-700
                           hover:shadow-xl hover:shadow-blue-50 dark:hover:shadow-blue-950
                           bg-white dark:bg-slate-800 transition-all duration-300 hover:-translate-y-1">
                <div className={`w-12 h-12 ${f.bg} rounded-xl flex items-center justify-center mb-4`}>
                  <div className={`bg-gradient-to-br ${f.color} bg-clip-text`} style={{color: 'transparent'}}>
                    <div className={`[&_svg]:stroke-current bg-gradient-to-br ${f.color}`}
                         style={{WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent'}}>
                    </div>
                  </div>
                  <span className={`bg-gradient-to-br ${f.color} inline-flex`}
                        style={{WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent'}}>
                    {f.icon}
                  </span>
                </div>
                <h3 className="font-bold text-gray-900 dark:text-white text-lg mb-2">{f.title}</h3>
                <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section id="how-it-works" className="py-24 px-4 sm:px-6 bg-slate-50 dark:bg-slate-950">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-violet-600 dark:text-violet-400 uppercase tracking-widest mb-3">Process</p>
            <h2 className="section-heading mb-4">How it works</h2>
            <p className="section-sub">Three simple steps from problem to resolution.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {STEPS.map((s, i) => (
              <div key={s.num} className="relative text-center">
                {i < STEPS.length - 1 && (
                  <div className="hidden md:block absolute top-8 left-[calc(50%+3rem)] w-[calc(100%-6rem)] h-px bg-gradient-to-r from-gray-200 to-gray-100 dark:from-slate-700 dark:to-slate-800" />
                )}
                <div className={`w-16 h-16 ${s.bg} border-2 ${s.border} rounded-2xl flex items-center justify-center mx-auto mb-5`}>
                  <span className={`text-2xl font-extrabold ${s.color}`}>{s.num}</span>
                </div>
                <h3 className="font-bold text-gray-900 dark:text-white text-lg mb-2">{s.title}</h3>
                <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CHANNELS ── */}
      <section id="channels" className="py-24 px-4 sm:px-6 bg-white dark:bg-slate-900">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-widest mb-3">Channels</p>
            <h2 className="section-heading mb-4">Reach us your way</h2>
            <p className="section-sub">One AI agent. Three channels. Zero compromise on quality.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {CHANNELS.map(ch => (
              <div key={ch.title}
                className={`rounded-2xl border ${ch.border} ${ch.bg} p-8 flex flex-col gap-4
                             hover:shadow-xl transition-all duration-300 hover:-translate-y-1`}>
                <div className="flex items-start justify-between">
                  <span className={ch.color}>{ch.icon}</span>
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${ch.tagColor}`}>{ch.tag}</span>
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-white text-xl mb-2">{ch.title}</h3>
                  <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed">{ch.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA BANNER ── */}
      <section className="py-24 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto">
          <div className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-blue-600 to-violet-700 p-12 text-center text-white shadow-2xl">
            {/* Background decoration */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
            <div className="absolute bottom-0 left-0 w-64 h-64 bg-white/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />

            <div className="relative z-10">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/20 rounded-full text-sm font-medium mb-6">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                AI Agent ready
              </div>
              <h2 className="text-4xl md:text-5xl font-extrabold mb-4">
                Need help right now?
              </h2>
              <p className="text-blue-100 text-lg mb-10 max-w-xl mx-auto">
                Our AI agent is online and ready to solve your issue in under 5 seconds.
                No hold music. No bots. Just answers.
              </p>
              <Link href="/support"
                className="inline-flex items-center gap-2 bg-white text-blue-700 font-bold py-4 px-10 rounded-2xl
                           hover:bg-blue-50 transition-all duration-200 shadow-xl hover:shadow-2xl hover:-translate-y-1 text-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                Start a Support Chat
              </Link>
            </div>
          </div>
        </div>
      </section>

    </div>
  );
}

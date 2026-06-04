import Link from "next/link";

const features = [
  {
    icon: "🔔",
    bg: "bg-orange-100",
    title: "Smart Alerts",
    desc: "Get instant notifications via WhatsApp, web, or mobile when deals match your preferences.",
  },
  {
    icon: "🏷️",
    bg: "bg-red-100",
    title: "Brand Tracking",
    desc: "Follow your favourite brands and get notified the moment they launch sales or promotions.",
  },
  {
    icon: "📍",
    bg: "bg-green-100",
    title: "Location-Based",
    desc: "Discover deals near you from local stores and businesses in your area.",
  },
  {
    icon: "📱",
    bg: "bg-blue-100",
    title: "Multi-Platform",
    desc: "Access deals anywhere with our web app, WhatsApp integration, and mobile apps.",
  },
  {
    icon: "⚡",
    bg: "bg-yellow-100",
    title: "Real-Time Updates",
    desc: "Lightning-fast notifications ensure you catch time-sensitive deals before they expire.",
  },
  {
    icon: "🕐",
    bg: "bg-violet-100",
    title: "24/7 Monitoring",
    desc: "We continuously scan for deals around the clock so you can save while you sleep.",
  },
];

const steps = [
  {
    n: "1",
    title: "Choose Your Interests",
    desc: "Select brands, product categories, and locations you want to track for deals.",
  },
  {
    n: "2",
    title: "Set Your Preferences",
    desc: "Customize alert settings and choose how you want to receive notifications.",
  },
  {
    n: "3",
    title: "Start Saving",
    desc: "Sit back and let us notify you about the best deals tailored to your interests.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* ── Navbar ── */}
      <header className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-brand-600 text-lg">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z" />
              <circle cx="7.5" cy="7.5" r=".5" fill="currentColor" />
            </svg>
            <span>Bargain Hunters</span>
          </div>
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-gray-600">
            <a href="#how-it-works" className="hover:text-brand-600 transition">
              How It Works
            </a>
            <a href="#features" className="hover:text-brand-600 transition">
              Features
            </a>
          </nav>
          <Link
            href="/login"
            className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition flex items-center gap-2"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="15"
              height="15"
              fill="currentColor"
              viewBox="0 0 16 16"
            >
              <path d="M13.601 2.326A7.85 7.85 0 0 0 7.994 0C3.627 0 .068 3.558.064 7.926c0 1.399.366 2.76 1.057 3.965L0 16l4.204-1.102a7.9 7.9 0 0 0 3.79.965h.004c4.368 0 7.926-3.558 7.93-7.93A7.9 7.9 0 0 0 13.6 2.326zM7.994 14.521a6.6 6.6 0 0 1-3.356-.92l-.24-.144-2.494.654.666-2.433-.156-.251a6.56 6.56 0 0 1-1.007-3.505c0-3.626 2.957-6.584 6.591-6.584a6.56 6.56 0 0 1 4.66 1.931 6.56 6.56 0 0 1 1.928 4.66c-.004 3.639-2.961 6.592-6.592 6.592m3.615-4.934c-.197-.099-1.17-.578-1.353-.646-.182-.065-.315-.099-.445.099-.133.197-.513.646-.627.775-.114.133-.232.148-.43.05-.197-.1-.836-.308-1.592-.985-.59-.525-.985-1.175-1.103-1.372-.114-.198-.011-.304.088-.403.087-.088.197-.232.296-.346.1-.114.133-.198.198-.33.065-.134.034-.248-.015-.347-.05-.099-.445-1.076-.612-1.47-.16-.389-.323-.335-.445-.34-.114-.007-.247-.007-.38-.007a.73.73 0 0 0-.529.247c-.182.198-.691.677-.691 1.654s.71 1.916.81 2.049c.098.133 1.394 2.132 3.383 2.992.47.205.84.326 1.129.418.475.152.904.129 1.246.08.38-.058 1.171-.48 1.338-.943.164-.464.164-.86.114-.943-.049-.084-.182-.133-.38-.232" />
            </svg>
            Get Started
          </Link>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="bg-[#FFF9F1] py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Left */}
            <div>
              <span className="inline-block bg-brand-100 text-brand-700 text-sm font-semibold px-4 py-1.5 rounded-full mb-6">
                Never Miss a Deal Again
              </span>
              <h1 className="text-5xl font-bold text-gray-900 leading-tight mb-4">
                Smart Alerts for{" "}
                <span className="text-brand-600">Every Deal</span>
              </h1>
              <p className="text-gray-500 text-lg leading-relaxed mb-8">
                Get instant notifications for deals and discounts across your favourite brands,
                products, and locations. Available on web, WhatsApp, and mobile apps.
              </p>

              <div className="flex flex-wrap items-center gap-3 mb-10">
                <Link
                  href="/login"
                  className="bg-brand-600 hover:bg-brand-700 text-white font-semibold px-6 py-3 rounded-lg transition flex items-center gap-2"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    fill="currentColor"
                    viewBox="0 0 16 16"
                  >
                    <path d="M13.601 2.326A7.85 7.85 0 0 0 7.994 0C3.627 0 .068 3.558.064 7.926c0 1.399.366 2.76 1.057 3.965L0 16l4.204-1.102a7.9 7.9 0 0 0 3.79.965h.004c4.368 0 7.926-3.558 7.93-7.93A7.9 7.9 0 0 0 13.6 2.326zM7.994 14.521a6.6 6.6 0 0 1-3.356-.92l-.24-.144-2.494.654.666-2.433-.156-.251a6.56 6.56 0 0 1-1.007-3.505c0-3.626 2.957-6.584 6.591-6.584a6.56 6.56 0 0 1 4.66 1.931 6.56 6.56 0 0 1 1.928 4.66c-.004 3.639-2.961 6.592-6.592 6.592m3.615-4.934c-.197-.099-1.17-.578-1.353-.646-.182-.065-.315-.099-.445.099-.133.197-.513.646-.627.775-.114.133-.232.148-.43.05-.197-.1-.836-.308-1.592-.985-.59-.525-.985-1.175-1.103-1.372-.114-.198-.011-.304.088-.403.087-.088.197-.232.296-.346.1-.114.133-.198.198-.33.065-.134.034-.248-.015-.347-.05-.099-.445-1.076-.612-1.47-.16-.389-.323-.335-.445-.34-.114-.007-.247-.007-.38-.007a.73.73 0 0 0-.529.247c-.182.198-.691.677-.691 1.654s.71 1.916.81 2.049c.098.133 1.394 2.132 3.383 2.992.47.205.84.326 1.129.418.475.152.904.129 1.246.08.38-.058 1.171-.48 1.338-.943.164-.464.164-.86.114-.943-.049-.084-.182-.133-.38-.232" />
                  </svg>
                  Get Started Free
                </Link>
                <a
                  href="#"
                  className="bg-gray-900 text-white font-semibold px-4 py-3 rounded-lg transition hover:bg-gray-700 text-sm"
                >
                  App Store
                </a>
                <a
                  href="#"
                  className="bg-gray-900 text-white font-semibold px-4 py-3 rounded-lg transition hover:bg-gray-700 text-sm"
                >
                  Google Play
                </a>
              </div>

              <div className="flex gap-8">
                <div>
                  <p className="text-3xl font-bold text-gray-900">50K+</p>
                  <p className="text-sm text-gray-500">Active Users</p>
                </div>
                <div>
                  <p className="text-3xl font-bold text-gray-900">1M+</p>
                  <p className="text-sm text-gray-500">Deals Tracked</p>
                </div>
                <div>
                  <p className="text-3xl font-bold text-gray-900">24/7</p>
                  <p className="text-sm text-gray-500">Monitoring</p>
                </div>
              </div>
            </div>

            {/* Right — phone mockup */}
            <div className="flex justify-center">
              <div className="relative w-72">
                <div className="bg-gray-900 rounded-[2.5rem] p-3 shadow-2xl">
                  <div className="bg-white rounded-[2rem] overflow-hidden" style={{ aspectRatio: "9/19" }}>
                    <div className="bg-brand-600 px-5 py-6 text-white">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-lg">Bargain Hunters</span>
                        <span>🔔</span>
                      </div>
                      <p className="text-orange-100 text-xs">Your personal deal finder</p>
                    </div>
                    <div className="bg-gray-50 px-4 -mt-3 mb-4">
                      <div className="bg-white rounded-xl shadow px-3 py-2.5 mt-3">
                        <p className="text-xs text-gray-400">Search brands, products…</p>
                      </div>
                    </div>
                    <div className="px-4 space-y-3 pb-6">
                      {[
                        { icon: "🏷️", label: "50% OFF", bg: "bg-red-100", title: "Nike Air Max", sub: "Limited time offer" },
                        { icon: "⚡", label: "30% OFF", bg: "bg-green-100", title: "Electronics Sale", sub: "Ends tonight" },
                        { icon: "📍", label: "NEARBY", bg: "bg-orange-100", title: "Local Store Deal", sub: "2.5 km away" },
                      ].map((card) => (
                        <div key={card.title} className="bg-white rounded-xl p-3 shadow-sm border border-gray-100 flex items-center gap-3">
                          <div className={`w-10 h-10 ${card.bg} rounded-lg flex items-center justify-center text-lg`}>
                            {card.icon}
                          </div>
                          <div>
                            <span className="inline-block bg-gray-100 text-gray-700 text-[10px] font-bold px-2 py-0.5 rounded mb-0.5">
                              {card.label}
                            </span>
                            <p className="text-xs font-semibold text-gray-900">{card.title}</p>
                            <p className="text-[10px] text-gray-400">{card.sub}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                {/* Floating badge */}
                <div className="absolute -left-10 top-16 bg-white rounded-xl shadow-xl p-3 border border-gray-100 hidden lg:block">
                  <div className="flex items-center gap-2 text-sm">
                    <span>🔔</span>
                    <span className="font-medium text-gray-900">New Deal Alert!</span>
                  </div>
                </div>
                <div className="absolute -right-10 bottom-24 bg-white rounded-xl shadow-xl p-3 border border-gray-100 hidden lg:block text-center">
                  <p className="text-xl font-bold text-green-600">-60%</p>
                  <p className="text-[10px] text-gray-500">Today Only</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900 mb-3">
              Everything You Need to Save Big
            </h2>
            <p className="text-gray-500 text-lg max-w-xl mx-auto">
              Powerful features to help you never miss a deal on products and brands you love.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div
                key={f.title}
                className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow"
              >
                <div className={`w-12 h-12 ${f.bg} rounded-xl flex items-center justify-center text-2xl mb-4`}>
                  {f.icon}
                </div>
                <h3 className="font-bold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section id="how-it-works" className="py-20 bg-[#F9FAFC]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900 mb-3">
              Start Saving in 3 Simple Steps
            </h2>
            <p className="text-gray-500 text-lg">Get started in under a minute</p>
          </div>
          <div className="flex flex-col md:flex-row gap-10 justify-center">
            {steps.map((s) => (
              <div key={s.n} className="flex flex-col items-center text-center max-w-xs mx-auto">
                <div className="w-16 h-16 rounded-full bg-brand-600 text-white flex items-center justify-center text-2xl font-bold mb-5">
                  {s.n}
                </div>
                <h3 className="font-bold text-gray-900 mb-2 text-lg">{s.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="bg-brand-600 py-20 text-white text-center">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-4xl font-bold mb-4">Ready to Start Saving?</h2>
          <p className="text-orange-100 text-lg mb-8 max-w-md mx-auto">
            Join thousands of smart shoppers who never miss a great deal.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              href="/login"
              className="bg-white text-brand-600 font-bold px-8 py-3 rounded-lg hover:bg-orange-50 transition"
            >
              Sign In / Register
            </Link>
            <a
              href="#"
              className="bg-white/10 text-white font-semibold px-8 py-3 rounded-lg hover:bg-white/20 transition border border-white/30"
            >
              Download App
            </a>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="bg-[#111827] text-gray-400 py-14">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
            <div>
              <div className="flex items-center gap-2 text-white font-bold text-lg mb-3">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#E54416"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z" />
                  <circle cx="7.5" cy="7.5" r=".5" fill="#E54416" />
                </svg>
                Bargain Hunters
              </div>
              <p className="text-sm leading-relaxed">
                Your smart companion for finding the best deals and discounts.
              </p>
            </div>
            {[
              { heading: "Product", links: ["Features", "How it Works", "Pricing"] },
              { heading: "Company", links: ["About", "Blog", "Careers"] },
              { heading: "Support", links: ["Help Center", "Contact", "Privacy Policy"] },
            ].map((col) => (
              <div key={col.heading}>
                <p className="text-white font-semibold mb-3">{col.heading}</p>
                <ul className="space-y-2 text-sm">
                  {col.links.map((l) => (
                    <li key={l}>
                      <a href="#" className="hover:text-white transition">
                        {l}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <hr className="border-gray-700 mb-6" />
          <p className="text-center text-sm">
            © {new Date().getFullYear()} Bargain Hunters. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}

"use client";

import { useEffect, useState, useRef } from "react";

const locations = [
  { city: "Sensor Networks", region: "IoT Devices", latency: "Real-time" },
  { city: "Satellite Feeds", region: "EO Imagery", latency: "Near real-time" },
  { city: "Weather Services", region: "NOAA / ECMWF", latency: "< 5 min" },
  { city: "Citizen Reports", region: "Mobile / Web", latency: "Instant" },
  { city: "Social Media", region: "Public Signals", latency: "Streaming" },
  { city: "Government Feeds", region: "FEMA / USGS", latency: "Continuous" },
];

export function InfrastructureSection() {
  const [isVisible, setIsVisible] = useState(false);
  const [activeLocation, setActiveLocation] = useState(0);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveLocation((prev) => (prev + 1) % locations.length);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          {/* Left: Content */}
          <div
            className={`transition-all duration-700 ${
              isVisible ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-8"
            }`}
          >
            <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
              <span className="w-8 h-px bg-foreground/30" />
              Data Sources
            </span>
            <h2 className="text-4xl lg:text-6xl font-display tracking-tight mb-8">
              Multi-source
              <br />
              data fusion.
            </h2>
            <p className="text-xl text-muted-foreground leading-relaxed mb-12">
              Ingests sensor, satellite, weather, and citizen data into a single 
              operational picture. Every data type is normalized, deduplicated, 
              and clustered into actionable incidents.
            </p>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-8">
              <div>
                <div className="text-4xl lg:text-5xl font-display mb-2">4+</div>
                <div className="text-sm text-muted-foreground">Data source types</div>
              </div>
              <div>
                <div className="text-4xl lg:text-5xl font-display mb-2">Real-time</div>
                <div className="text-sm text-muted-foreground">Event streaming</div>
              </div>
              <div>
                <div className="text-4xl lg:text-5xl font-display mb-2">Auto</div>
                <div className="text-sm text-muted-foreground">Alert deduplication</div>
              </div>
            </div>
          </div>

          {/* Right: Location list */}
          <div
            className={`transition-all duration-700 delay-200 ${
              isVisible ? "opacity-100 translate-x-0" : "opacity-0 translate-x-8"
            }`}
          >
            <div className="border border-foreground/10">
              {/* Header */}
              <div className="px-6 py-4 border-b border-foreground/10 flex items-center justify-between">
                <span className="text-sm font-mono text-muted-foreground">Data Sources</span>
                <span className="flex items-center gap-2 text-xs font-mono text-green-600">
                  <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  All feeds active
                </span>
              </div>

              {/* Locations */}
              <div>
                {locations.map((location, index) => (
                  <div
                    key={location.city}
                    className={`px-6 py-5 border-b border-foreground/5 last:border-b-0 flex items-center justify-between transition-all duration-300 ${
                      activeLocation === index ? "bg-foreground/[0.02]" : ""
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <span 
                        className={`w-2 h-2 rounded-full transition-colors duration-300 ${
                          activeLocation === index ? "bg-foreground" : "bg-foreground/20"
                        }`}
                      />
                      <div>
                        <div className="font-medium">{location.city}</div>
                        <div className="text-sm text-muted-foreground">{location.region}</div>
                      </div>
                    </div>
                    <span className="font-mono text-sm text-muted-foreground">{location.latency}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

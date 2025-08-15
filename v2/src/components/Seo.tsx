import React, { useEffect } from "react";

interface SeoProps {
  title: string;
  description: string;
  canonical?: string;
  jsonLd?: Record<string, any>;
}

const ensureMeta = (name: string, content: string) => {
  let el = document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute("name", name);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
};

const ensureProperty = (property: string, content: string) => {
  let el = document.querySelector<HTMLMetaElement>(`meta[property="${property}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute("property", property);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
};

const ensureLink = (rel: string, href: string) => {
  let el = document.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`);
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", rel);
    document.head.appendChild(el);
  }
  el.setAttribute("href", href);
};

const Seo: React.FC<SeoProps> = ({ title, description, canonical, jsonLd }) => {
  useEffect(() => {
    document.title = title;
    ensureMeta("description", description);
    ensureProperty("og:title", title);
    ensureProperty("og:description", description);
    ensureMeta("twitter:title", title);
    ensureMeta("twitter:description", description);

    if (canonical) ensureLink("canonical", canonical);

    // JSON-LD
    const id = "json-ld";
    const existing = document.getElementById(id);
    if (existing) existing.remove();
    if (jsonLd) {
      const script = document.createElement("script");
      script.type = "application/ld+json";
      script.id = id;
      script.text = JSON.stringify(jsonLd);
      document.head.appendChild(script);
    }
  }, [title, description, canonical, jsonLd]);

  return null;
};

export default Seo;

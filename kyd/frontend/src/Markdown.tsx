import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { fmt, type Obs } from './api';

/** Agent and document text. Raw HTML in the Markdown is never rendered. [obs:id] citations become footnote
 *  markers that show the figure's label, value and vintage on hover. */
export function Markdown({ text, obs = {} }: { text: string; obs?: Record<string, Obs> }) {
  const src = text.replace(/\[obs:([^\]\s]+)\]/g, (_, id) => `[${obs[id]?.indicator ?? 'src'}](#obs:${encodeURIComponent(id)})`);
  const components: Components = {
    a: ({ href = '', children }) => {
      if (href.startsWith('#obs:')) {
        const o = obs[decodeURIComponent(href.slice(5))];
        return <sup className="text-cyan-500 ml-0.5" title={o ? `${o.label}: ${fmt(o)} · ${o.vintage}` : href.slice(5)}>[{children}]</sup>;
      }
      return /^https?:\/\//.test(href)
        ? <a href={href} target="_blank" rel="noreferrer" className="text-cyan-400 underline break-all">{children}</a>
        : <span>{children}</span>;
    },
    h1: ({ children }) => <h1 className="text-lg font-semibold text-slate-100 mt-3 mb-1">{children}</h1>,
    h2: ({ children }) => <h2 className="text-base font-semibold text-slate-100 mt-3 mb-1">{children}</h2>,
    h3: ({ children }) => <h3 className="text-sm font-semibold text-slate-100 mt-2 mb-1">{children}</h3>,
    p: ({ children }) => <p className="my-1.5 leading-relaxed">{children}</p>,
    ul: ({ children }) => <ul className="my-1.5 list-disc ml-5 space-y-0.5">{children}</ul>,
    ol: ({ children }) => <ol className="my-1.5 list-decimal ml-5 space-y-0.5">{children}</ol>,
    strong: ({ children }) => <strong className="text-slate-100">{children}</strong>,
    table: ({ children }) => <div className="overflow-x-auto my-2"><table className="text-xs border-collapse">{children}</table></div>,
    th: ({ children }) => <th className="border-b border-premium-600 px-2 py-1 text-left text-slate-400 font-normal">{children}</th>,
    td: ({ children }) => <td className="border-b border-premium-800 px-2 py-1">{children}</td>,
    blockquote: ({ children }) => <blockquote className="border-l-2 border-premium-600 pl-3 text-slate-400">{children}</blockquote>,
    code: ({ children }) => <code className="font-mono text-xs bg-premium-950 px-1 rounded">{children}</code>,
  };
  return <div className="kyd-md text-sm">
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{src}</ReactMarkdown>
  </div>;
}

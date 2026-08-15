export default function SidePanel({ children }: { children: React.ReactNode }) {
  return (
    <div className="glass-panel absolute top-4 right-4 z-30 max-h-[80vh] w-[340px] overflow-y-auto p-4">
      {children}
    </div>
  );
}

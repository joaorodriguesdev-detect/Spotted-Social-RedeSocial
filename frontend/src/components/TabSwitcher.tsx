"use client";

interface Tab {
  id: string;
  label: string;
}

interface TabSwitcherProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export default function TabSwitcher({ tabs, activeTab, onTabChange }: TabSwitcherProps) {
  return (
    <div className="flex border-b border-zinc-800/60 bg-black">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`relative flex-1 py-3 text-sm font-medium transition-colors ${
              isActive
                ? "text-zinc-100"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {tab.label}
            {isActive && (
              <span className="absolute bottom-0 left-[15%] right-[15%] h-[3px] rounded-full bg-gradient-to-r from-emerald-400 to-violet-500" />
            )}
          </button>
        );
      })}
    </div>
  );
}

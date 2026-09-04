import { FolderX } from 'lucide-react'

export function EmptyState({ title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 border-2 border-dashed border-border/80 rounded-2xl bg-surface/50 dark:bg-surface/20 hover:bg-surface dark:hover:bg-surface/50 transition-all duration-300 shadow-sm hover:shadow-soft group">
      <div className="bg-brand-mint/50 dark:bg-brand-primary/10 p-4 rounded-xl shadow-sm mb-5 border border-brand-primary/10 text-brand-primary dark:text-brand-teal group-hover:scale-105 transition-transform duration-300">
        <FolderX className="w-8 h-8 opacity-80" />
      </div>
      <h3 className="text-xl font-bold text-foreground mb-2 tracking-tight">{title}</h3>
      <p className="text-base text-muted mb-8 text-center max-w-md leading-relaxed">{description}</p>
      {action}
    </div>
  )
}

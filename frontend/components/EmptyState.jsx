import { FolderX } from 'lucide-react'

export function EmptyState({ title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 border border-dashed border-gray-300 rounded-xl bg-gray-50/50">
      <div className="bg-white p-4 rounded-full shadow-sm mb-4 border border-gray-100">
        <FolderX className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>
      <p className="text-sm text-gray-500 mb-6 text-center max-w-sm">{description}</p>
      {action}
    </div>
  )
}

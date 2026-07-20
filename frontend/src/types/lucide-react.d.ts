declare module 'lucide-react' {
  import { FC } from 'react'
  export interface LucideProps {
    size?: number | string
    color?: string
    strokeWidth?: number | string
    absoluteStrokeWidth?: boolean
    className?: string
  }
  export type Icon = FC<LucideProps>
  export const LayoutDashboard: Icon
  export const Rocket: Icon
  export const Search: Icon
  export const Building2: Icon
  export const Target: Icon
  export const Mail: Icon
  export const FileText: Icon
  export const History: Icon
  export const LogOut: Icon
}

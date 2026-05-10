import { redirect } from 'next/navigation'

/** Home page CTA uses /classification; MRI workflow lives under /detection. */
export default function ClassificationPage() {
  redirect('/detection')
}

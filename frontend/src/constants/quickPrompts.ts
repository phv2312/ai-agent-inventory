export interface QuickPrompt {
    id: string;
    label: string;
    template: string;
}

export const QUICK_PROMPTS: QuickPrompt[] = [
    {
        id: 'search-docs',
        label: 'Search my documents',
        template: 'Search my indexed documents for ',
    },
    {
        id: 'summarize-pdf',
        label: 'Summarize a PDF',
        template: 'Summarize the key points from ',
    },
    {
        id: 'compare-policies',
        label: 'Compare policies',
        template: 'Compare these policies and highlight differences: ',
    },
    {
        id: 'draft-sources',
        label: 'Draft from sources',
        template: 'Draft a response using information from my sources about ',
    },
];

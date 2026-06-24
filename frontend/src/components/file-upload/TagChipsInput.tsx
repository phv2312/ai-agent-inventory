import React, { useState, useEffect, useRef } from 'react';
import type { KeyboardEvent } from 'react';
import { fetchMetadataSuggestions } from '../../hooks/useMetadataSuggestions';

interface TagChipsInputProps {
    value: string; // Comma separated string of keywords
    onChange: (value: string) => void;
    placeholder?: string;
    disabled?: boolean;
}

export function TagChipsInput({ value, onChange, placeholder = "Add keyword...", disabled = false }: TagChipsInputProps) {
    const [inputValue, setInputValue] = useState('');
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [allTags, setAllTags] = useState<string[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const tags = value.split(',').map(t => t.trim()).filter(t => t.length > 0);

    useEffect(() => {
        // Load existing tags for autocomplete
        fetchMetadataSuggestions().then(data => {
            setAllTags(data['keywords'] || []);
        }).catch(err => {
            console.warn('Failed to load metadata values for autocomplete:', err);
        });
    }, []);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setShowSuggestions(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setInputValue(val);

        if (val.trim()) {
            const filtered = allTags.filter(t =>
                t.toLowerCase().includes(val.toLowerCase()) &&
                !tags.includes(t)
            );
            setSuggestions(filtered);
            setShowSuggestions(true);
        } else {
            setShowSuggestions(false);
        }
    };

    const addTag = (tagToAdd: string) => {
        const cleanTag = tagToAdd.trim();
        if (!cleanTag) return;

        if (!tags.includes(cleanTag)) {
            const newTags = [...tags, cleanTag];
            onChange(newTags.join(', '));
        }
        setInputValue('');
        setShowSuggestions(false);
        inputRef.current?.focus();
    };

    const removeTag = (tagToRemove: string) => {
        const newTags = tags.filter(t => t !== tagToRemove);
        onChange(newTags.join(', '));
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addTag(inputValue);
        } else if (e.key === ',') {
            // Disallow commas as requested ("dont use ,")
            e.preventDefault();
        } else if (e.key === 'Backspace' && !inputValue && tags.length > 0) {
            removeTag(tags[tags.length - 1]);
        }
    };

    return (
        <div className="relative" ref={containerRef}>
            <div
                className={`flex flex-wrap gap-2 p-2 border border-slate-300 rounded-md bg-white focus-within:border-slate-400 min-h-[42px] items-center ${disabled ? 'opacity-60 cursor-not-allowed bg-slate-50' : ''}`}
                onClick={() => !disabled && inputRef.current?.focus()}
            >
                {tags.map((tag, idx) => (
                    <span
                        key={idx}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                    >
                        {tag}
                        {!disabled && (
                            <button
                                type="button"
                                onClick={(e) => { e.stopPropagation(); removeTag(tag); }}
                                className="hover:bg-blue-200 rounded-full p-0.5 text-blue-600 focus:outline-none"
                            >
                                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        )}
                    </span>
                ))}

                <input
                    ref={inputRef}
                    type="text"
                    value={inputValue}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    onFocus={() => inputValue.trim() && setShowSuggestions(true)}
                    disabled={disabled}
                    placeholder={tags.length === 0 ? placeholder : ''}
                    className="flex-1 min-w-[120px] outline-none bg-transparent text-sm text-slate-900 border-none px-1 py-0 shadow-none focus:ring-0"
                />
            </div>

            {/* Autocomplete Dropdown */}
            {showSuggestions && suggestions.length > 0 && !disabled && (
                <ul className="absolute z-10 w-full mt-1 bg-white border border-slate-200 rounded-md shadow-lg max-h-60 overflow-auto py-1 text-sm">
                    {suggestions.map((suggestion, idx) => (
                        <li
                            key={idx}
                            onClick={() => addTag(suggestion)}
                            className="px-4 py-2 cursor-pointer text-slate-700 hover:bg-slate-100 hover:text-slate-900"
                        >
                            {suggestion}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

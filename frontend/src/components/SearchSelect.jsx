import { useEffect, useRef, useState } from "react";

export default function SearchSelect({
    value,
    searchTerm,
    onSearchChange,
    options,
    onSelect,
    placeholder,
    emptyText = "Sonuç bulunamadı",
    disabled = false,
}) {
    const [acik, setAcik] = useState(false);
    const kutuRef = useRef(null);

    useEffect(() => {
        const disaTikla = (e) => {
            if (kutuRef.current && !kutuRef.current.contains(e.target)) {
                setAcik(false);
            }
        };
        document.addEventListener("mousedown", disaTikla);
        return () => document.removeEventListener("mousedown", disaTikla);
    }, []);

    const sec = (secenek) => {
        onSelect(secenek);
        setAcik(false);
    };

    return (
        <div className="relative" ref={kutuRef}>
            <input
                className="w-full border p-3 disabled:opacity-60"
                placeholder={placeholder}
                value={searchTerm}
                disabled={disabled}
                onFocus={() => setAcik(true)}
                onChange={(e) => {
                    onSearchChange(e.target.value);
                    if (value) {
                        sec(null);
                    }
                    setAcik(true);
                }}
            />

            {acik && !disabled && (
                <ul className="absolute z-20 mt-1 w-full max-h-64 overflow-auto border bg-[#FFFDF8] shadow-lg">
                    {options.length === 0 && (
                        <li className="p-3 text-sm text-gray-500">{emptyText}</li>
                    )}
                    {options.map((secenek) => (
                        <li key={secenek.id}>
                            <button
                                type="button"
                                className={`w-full text-left p-3 hover:bg-[#F8F2E8] ${
                                    value === secenek.id ? "bg-[#F8F2E8] font-semibold" : ""
                                }`}
                                onClick={() => sec(secenek)}
                            >
                                {secenek.name}
                            </button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
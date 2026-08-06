import { useEffect, useState } from "react";

// Her tuşta istek atılmaz: global limit 20/second ve dev'de StrictMode effect'i ikiye katlıyor.
export default function useDebounce(value, gecikme = 300) {

    const [gecikmeli, setGecikmeli] = useState(value);

    useEffect(() => {

        const zamanlayici = setTimeout(() => setGecikmeli(value), gecikme);

        return () => clearTimeout(zamanlayici);

    }, [value, gecikme]);

    return gecikmeli;

}

const VARSAYILAN = "Bir hata oluştu, lütfen tekrar deneyin";

// Pydantic v2, validator'daki raise ValueError/AssertionError mesajının başına kendi etiketini
// ekliyor; kullanıcıya sadece mesajın kendisi gösterilir.
const ETIKETLER = ["Value error, ", "Assertion failed, "];

function temizle(msg) {
    if (typeof msg !== "string") {
        return msg;
    }
    const etiket = ETIKETLER.find((e) => msg.startsWith(e));
    return etiket ? msg.slice(etiket.length) : msg;
}

// Backend üç ayrı gövde şekli döndürüyor: {detail: "..."}, {detail: [{msg}]} (422 pydantic),
// {error: "..."} (429 slowapi). Elle fırlatılan 422'lerde detail yine string.
export default function parseError(error, varsayilan = VARSAYILAN) {
    if (!error?.response) {
        return "Sunucuya ulaşılamadı";
    }

    const data = error.response.data;

    if (typeof data?.detail === "string") {
        return data.detail;
    }

    if (Array.isArray(data?.detail)) {
        const mesajlar = data.detail.map((d) => temizle(d?.msg)).filter(Boolean);
        if (mesajlar.length > 0) {
            return mesajlar.join(", ");
        }
    }

    if (typeof data?.error === "string") {
        return data.error;
    }

    return varsayilan;
}

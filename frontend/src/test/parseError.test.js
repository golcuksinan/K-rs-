import { describe, expect, it } from "vitest";

import parseError from "../api/parseError";


describe("parseError", () => {

    it("string detail'i olduğu gibi döndürür", () => {

        const hata = { response: { data: { detail: "Bu derse zaten yorum yaptınız" } } };

        expect(parseError(hata)).toBe("Bu derse zaten yorum yaptınız");

    });

    it("422 dizisindeki msg alanlarını birleştirir", () => {

        const hata = {
            response: {
                data: { detail: [{ msg: "Şifre en az 8 karakter" }, { msg: "Geçersiz e-posta" }] },
            },
        };

        expect(parseError(hata)).toBe("Şifre en az 8 karakter, Geçersiz e-posta");

    });

    it("pydantic'in eklediği etiketi kırpar", () => {

        const hata = {
            response: {
                data: {
                    detail: [
                        { msg: "Value error, Şifre en az bir rakam içermeli" },
                        { msg: "Assertion failed, Geçersiz yıl" },
                    ],
                },
            },
        };

        expect(parseError(hata)).toBe("Şifre en az bir rakam içermeli, Geçersiz yıl");

    });

    it("429'un {error} gövdesini okur", () => {

        const hata = { response: { data: { error: "Çok fazla istek" } } };

        expect(parseError(hata)).toBe("Çok fazla istek");

    });

    it("yanıt yoksa ağ hatası mesajı verir", () => {

        expect(parseError({})).toBe("Sunucuya ulaşılamadı");

    });

});

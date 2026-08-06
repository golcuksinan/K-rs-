import { describe, expect, it, vi } from "vitest";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { MemoryRouter, Route, Routes } from "react-router-dom";

import api from "../api/axios";

import AuthProvider from "../context/AuthContext";

import Register from "../pages/Auth/Register";
import VerifyOtp from "../pages/Auth/VerifyOtp";

import { sayfa } from "./yardimcilar";


vi.mock("../api/axios", () => ({
    default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));


const ekranaBas = () =>
    render(
        <MemoryRouter initialEntries={["/kayit"]}>
            <AuthProvider>
                <Routes>
                    <Route path="/kayit" element={<Register />} />
                    <Route path="/kayit/dogrula" element={<VerifyOtp />} />
                </Routes>
            </AuthProvider>
        </MemoryRouter>
    );


describe("Register", () => {

    it("sözleşmedeki gövdeyi gönderip OTP ekranına geçer", async () => {

        api.get.mockImplementation((url) => {

            if (url === "/universities") {
                return sayfa([{ id: 1, name: "Pamukkale Üniversitesi" }]);
            }

            if (url === "/faculties") {
                return sayfa([{ id: 2, name: "Mühendislik Fakültesi" }]);
            }

            if (url === "/departments") {
                return sayfa([{ id: 3, name: "Bilgisayar Mühendisliği" }]);
            }

            return sayfa([]);

        });

        api.post.mockResolvedValue({ data: { message: "Doğrulama kodu gönderildi" } });

        ekranaBas();

        fireEvent.change(screen.getByPlaceholderText(/E-posta/), {
            target: { value: "ogrenci@pau.edu.tr" },
        });

        fireEvent.change(screen.getByPlaceholderText(/Şifre/), {
            target: { value: "sifre1234" },
        });

        fireEvent.change(screen.getByPlaceholderText(/giriş yılı/), {
            target: { value: "2023" },
        });

        await screen.findByRole("option", { name: "Pamukkale Üniversitesi" });

        fireEvent.change(screen.getByDisplayValue("Üniversite seçin"), { target: { value: "1" } });

        await screen.findByRole("option", { name: "Mühendislik Fakültesi" });

        fireEvent.change(screen.getByDisplayValue("Fakülte seçin"), { target: { value: "2" } });

        await screen.findByRole("option", { name: "Bilgisayar Mühendisliği" });

        fireEvent.change(screen.getByDisplayValue("Bölüm seçin"), { target: { value: "3" } });

        fireEvent.click(screen.getByRole("button", { name: "Kayıt Ol" }));

        await waitFor(() =>

            expect(api.post).toHaveBeenCalledWith("/auth/register", {
                email: "ogrenci@pau.edu.tr",
                password: "sifre1234",
                department_id: 3,
                enrollment_year: 2023,
            })

        );

        expect(await screen.findByText("E-postanı Doğrula")).toBeInTheDocument();

    });

});

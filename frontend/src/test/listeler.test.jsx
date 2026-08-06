import { describe, expect, it, vi } from "vitest";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { MemoryRouter, Route, Routes } from "react-router-dom";

import api from "../api/axios";

import Courses from "../pages/Courses/Courses";
import Faculties from "../pages/Faculties";

import { sayfa } from "./yardimcilar";


vi.mock("../api/axios", () => ({
    default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));


describe("liste sayfaları zorunlu parametreleri geçer", () => {

    it("fakülteler university_id ile istenir", async () => {

        api.get.mockImplementation(() => sayfa([]));

        render(
            <MemoryRouter initialEntries={["/universiteler/5/fakulteler"]}>
                <Routes>
                    <Route path="/universiteler/:universityId/fakulteler" element={<Faculties />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() =>

            expect(api.get).toHaveBeenCalledWith("/faculties", {
                params: { university_id: "5", search: undefined, limit: 24, offset: 0 },
            })

        );

    });

    it("dersler department_id ile istenir", async () => {

        api.get.mockImplementation(() => sayfa([]));

        render(
            <MemoryRouter initialEntries={["/dersler?department_id=9"]}>
                <Courses />
            </MemoryRouter>
        );

        await waitFor(() =>

            expect(api.get).toHaveBeenCalledWith("/courses", {
                params: { department_id: "9", search: undefined, limit: 24, offset: 0 },
            })

        );

    });

    it("dersler parametresiz istenmez, iki karakterden sonra aranır", async () => {

        api.get.mockImplementation(() => sayfa([]));

        render(
            <MemoryRouter initialEntries={["/dersler"]}>
                <Courses />
            </MemoryRouter>
        );

        // Tek karakterde backend 422 döner; istek hiç atılmamalı.
        fireEvent.change(screen.getByPlaceholderText(/ara/i), { target: { value: "a" } });

        await new Promise((coz) => setTimeout(coz, 400));

        expect(api.get).not.toHaveBeenCalled();

        fireEvent.change(screen.getByPlaceholderText(/ara/i), { target: { value: "algo" } });

        await waitFor(() =>

            expect(api.get).toHaveBeenCalledWith("/courses", {
                params: { department_id: undefined, search: "algo", limit: 24, offset: 0 },
            })

        );

    });

});

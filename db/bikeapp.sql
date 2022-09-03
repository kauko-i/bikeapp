--
-- PostgreSQL database dump
--

-- Dumped from database version 14.5 (Ubuntu 14.5-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.5 (Ubuntu 14.5-0ubuntu0.22.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: journeys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.journeys (
    departure_time timestamp without time zone,
    return_time timestamp without time zone,
    departure_station character varying(3),
    return_station character varying(3),
    distance numeric,
    duration numeric
);


ALTER TABLE public.journeys OWNER TO postgres;

--
-- Name: stations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stations (
    id character varying(3),
    nimi character varying(256),
    namn character varying(256),
    name character varying(256),
    address character varying(256),
    adress character varying(256),
    city character varying(256),
    stad character varying(256),
    operator character varying(256),
    capacity integer,
    lat numeric,
    lon numeric
);


ALTER TABLE public.stations OWNER TO postgres;

--
-- Data for Name: journeys; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.journeys (departure_time, return_time, departure_station, return_station, distance, duration) FROM stdin;
\.


--
-- Data for Name: stations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.stations (id, nimi, namn, name, address, adress, city, stad, operator, capacity, lat, lon) FROM stdin;
\.


--
-- PostgreSQL database dump complete
--

